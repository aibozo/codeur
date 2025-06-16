"""
Context Graph RAG Enhancement System.

This module integrates the adaptive similarity gating and quality critic
with the context graph to provide intelligent context resolution.
"""

import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

from .context_graph import ContextGraph
from .context_graph_models import (
    MessageNode, MessageCommunity, ResolutionLevel,
    ResolutionConfig, ContextWindow
)
from .context_compiler import ContextCompiler, ResolutionStrategy
from ..core.adaptive_similarity_gate import AdaptiveSimilarityGate, RetrievalResult
from ..core.context_quality_critic import ContextQualityCritic, ContextChunk
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RAGEnhancedWindow(ContextWindow):
    """Extended context window with RAG enhancements."""
    rag_chunks: List[RetrievalResult] = field(default_factory=list)
    quality_score: float = 0.0
    critique_summary: Dict[str, Any] = field(default_factory=dict)
    adaptive_threshold: float = 0.7


class SimilarityBasedResolutionStrategy(ResolutionStrategy):
    """Resolution strategy that uses semantic similarity for intelligent context inclusion."""
    
    def __init__(self, 
                 similarity_gate: AdaptiveSimilarityGate,
                 project_id: str,
                 query: str):
        self.similarity_gate = similarity_gate
        self.project_id = project_id
        self.query = query
        self.node_similarities: Dict[str, float] = {}
    
    def calculate_resolution(self, 
                           node: MessageNode, 
                           distance: int,
                           config: ResolutionConfig) -> ResolutionLevel:
        """Calculate resolution using semantic similarity."""
        # Get or compute similarity
        similarity = self.node_similarities.get(node.id, 0.0)
        
        # Combine distance and similarity for resolution
        if distance <= config.full_context_distance:
            return ResolutionLevel.FULL
        
        # Use similarity for older messages
        if similarity >= 0.8:  # High similarity
            return ResolutionLevel.FULL
        elif similarity >= 0.6:  # Medium similarity
            return ResolutionLevel.SUMMARY
        elif similarity >= 0.4:  # Low similarity
            return ResolutionLevel.TITLE
        else:
            return ResolutionLevel.HIDDEN


class ContextGraphRAGEnhancer:
    """
    Enhances context graph with RAG capabilities and adaptive similarity gating.
    
    Features:
    - Semantic similarity search for relevant historical context
    - Adaptive thresholding based on project patterns
    - Quality critique feedback loop
    - Community-aware retrieval
    """
    
    def __init__(self,
                 context_graph: ContextGraph,
                 rag_client: Optional[Any] = None,
                 similarity_gate: Optional[AdaptiveSimilarityGate] = None,
                 quality_critic: Optional[ContextQualityCritic] = None):
        """
        Initialize the RAG enhancer.
        
        Args:
            context_graph: The context graph to enhance
            rag_client: RAG client for similarity search
            similarity_gate: Adaptive similarity gating system
            quality_critic: Context quality critic
        """
        self.context_graph = context_graph
        self.rag_client = rag_client
        self.similarity_gate = similarity_gate or AdaptiveSimilarityGate()
        self.quality_critic = quality_critic or ContextQualityCritic()
        
        # Cache for embeddings
        self.embedding_cache: Dict[str, List[float]] = {}
        
        # Performance tracking
        self.retrieval_stats = {
            "total_retrievals": 0,
            "avg_chunks_retrieved": 0.0,
            "avg_quality_score": 0.0,
            "cache_hits": 0
        }
        
        logger.info("Initialized Context Graph RAG Enhancer")
    
    async def compile_enhanced_context(self,
                                     query: str,
                                     current_node_id: str,
                                     max_tokens: int = 8000,
                                     include_rag: bool = True,
                                     auto_critique: bool = True) -> RAGEnhancedWindow:
        """
        Compile an enhanced context window with RAG integration.
        
        Args:
            query: The current query/question
            current_node_id: Current position in context graph
            max_tokens: Maximum token budget
            include_rag: Whether to include RAG results
            auto_critique: Whether to run quality critique
            
        Returns:
            Enhanced context window
        """
        start_time = datetime.now()
        
        # Get base context from graph
        compiler = ContextCompiler(self.context_graph)
        base_window = await compiler.compile_context(
            current_node_id,
            max_tokens=max_tokens // 2  # Reserve half for RAG
        )
        
        # Create enhanced window
        enhanced_window = RAGEnhancedWindow(
            current_node_id=base_window.current_node_id,
            nodes=base_window.nodes,
            resolution_map=base_window.resolution_map,
            communities=base_window.communities,
            total_tokens=base_window.total_tokens,
            full_nodes=base_window.full_nodes,
            summary_nodes=base_window.summary_nodes,
            title_nodes=base_window.title_nodes,
            hidden_nodes=base_window.hidden_nodes
        )
        
        # Add RAG-enhanced context if enabled
        if include_rag and self.rag_client:
            rag_results = await self._retrieve_similar_context(
                query,
                current_node_id,
                max_tokens=max_tokens // 2
            )
            enhanced_window.rag_chunks = rag_results
            
            # Update token count
            for chunk in rag_results:
                if chunk.included:
                    # Estimate tokens
                    enhanced_window.total_tokens += len(chunk.content) // 4
        
        # Apply similarity-based resolution enhancement
        if self.similarity_gate:
            await self._enhance_with_similarity(
                enhanced_window,
                query,
                current_node_id
            )
        
        # Run quality critique if enabled
        if auto_critique and self.quality_critic:
            critique = await self._critique_context(
                query,
                enhanced_window
            )
            enhanced_window.quality_score = critique.overall_quality
            enhanced_window.critique_summary = {
                "quality_score": critique.overall_quality,
                "blindspots": len(critique.blindspots),
                "unnecessary_chunks": len(critique.unnecessary_chunks),
                "suggestions": critique.suggestions[:3]  # Top 3 suggestions
            }
            
            # Provide feedback to similarity gate
            if self.similarity_gate and rag_results:
                await self._provide_gating_feedback(
                    query,
                    rag_results,
                    critique
                )
        
        # Update stats
        self.retrieval_stats["total_retrievals"] += 1
        if enhanced_window.rag_chunks:
            chunks_retrieved = sum(1 for c in enhanced_window.rag_chunks if c.included)
            self.retrieval_stats["avg_chunks_retrieved"] = (
                (self.retrieval_stats["avg_chunks_retrieved"] * 
                 (self.retrieval_stats["total_retrievals"] - 1) +
                 chunks_retrieved) / 
                self.retrieval_stats["total_retrievals"]
            )
        
        compile_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Compiled enhanced context in {compile_time:.2f}s "
            f"(tokens: {enhanced_window.total_tokens}, quality: {enhanced_window.quality_score:.2f})"
        )
        
        return enhanced_window
    
    async def _retrieve_similar_context(self,
                                      query: str,
                                      current_node_id: str,
                                      max_tokens: int) -> List[RetrievalResult]:
        """
        Retrieve similar context using RAG and adaptive gating.
        
        Args:
            query: Query for similarity search
            current_node_id: Current node for context
            max_tokens: Token budget for RAG chunks
            
        Returns:
            List of retrieval results
        """
        if not self.rag_client:
            return []
        
        try:
            # Search for similar content
            raw_results = self.rag_client.search(
                query=query,
                k=20,  # Get more than needed for gating
                filters={"project_id": self.context_graph.project_id}
            )
            
            # Apply adaptive similarity gating
            gated_results = self.similarity_gate.filter_results(
                results=raw_results,
                project_id=self.context_graph.project_id,
                retrieval_type="context_graph",
                target_chunks=int(max_tokens / 100),  # Rough estimate
                min_chunks=2,
                max_chunks=10
            )
            
            return gated_results
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []
    
    async def _enhance_with_similarity(self,
                                     window: RAGEnhancedWindow,
                                     query: str,
                                     current_node_id: str):
        """
        Enhance context window using similarity scores.
        
        Args:
            window: Context window to enhance
            query: Current query
            current_node_id: Current position
        """
        # Create similarity-based resolution strategy
        similarity_strategy = SimilarityBasedResolutionStrategy(
            self.similarity_gate,
            self.context_graph.project_id,
            query
        )
        
        # Compute similarities for graph nodes if we have embeddings
        if self.rag_client and hasattr(self.rag_client, 'get_embedding'):
            try:
                # Get query embedding
                query_embedding = await self._get_embedding(query)
                
                # Compute similarities for visible nodes
                for node in window.nodes:
                    if node.id != current_node_id:  # Skip current
                        node_embedding = await self._get_node_embedding(node)
                        if node_embedding and query_embedding:
                            similarity = self._cosine_similarity(
                                query_embedding,
                                node_embedding
                            )
                            similarity_strategy.node_similarities[node.id] = similarity
                
                # Re-calculate resolutions with similarity
                for node in window.nodes:
                    distance = self.context_graph.calculate_distance(
                        current_node_id,
                        node.id
                    )
                    new_resolution = similarity_strategy.calculate_resolution(
                        node,
                        distance,
                        self.context_graph.config
                    )
                    
                    # Only upgrade resolution, never downgrade
                    current_resolution = window.resolution_map[node.id]
                    if self._resolution_priority(new_resolution) > self._resolution_priority(current_resolution):
                        window.resolution_map[node.id] = new_resolution
                        logger.debug(
                            f"Upgraded node {node.id[:8]} from {current_resolution} to {new_resolution} "
                            f"based on similarity {similarity_strategy.node_similarities.get(node.id, 0):.3f}"
                        )
                        
            except Exception as e:
                logger.warning(f"Similarity enhancement failed: {e}")
    
    async def _critique_context(self,
                              query: str,
                              window: RAGEnhancedWindow) -> Any:
        """
        Run quality critique on the context window.
        
        Args:
            query: Current query
            window: Context window to critique
            
        Returns:
            Critique results
        """
        # Convert window content to chunks for critique
        context_chunks = []
        
        # Add graph nodes based on resolution
        for node in window.nodes:
            resolution = window.resolution_map.get(node.id, ResolutionLevel.HIDDEN)
            
            if resolution == ResolutionLevel.FULL:
                content = node.content
            elif resolution == ResolutionLevel.SUMMARY and node.summary:
                content = f"[Summary] {node.summary}"
            elif resolution == ResolutionLevel.TITLE:
                content = f"[Title] {node.content[:100]}..."
            else:
                continue  # Skip hidden
            
            context_chunks.append(ContextChunk(
                chunk_id=node.id,
                content=content,
                similarity_score=0.7,  # Default for graph nodes
                metadata={"type": "graph_node", "resolution": resolution.value}
            ))
        
        # Add RAG chunks
        for chunk in window.rag_chunks:
            if chunk.included:
                context_chunks.append(ContextChunk(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    similarity_score=chunk.similarity_score,
                    metadata=chunk.metadata
                ))
        
        # Run critique
        critique = await self.quality_critic.critique_context(
            query=query,
            context_chunks=context_chunks,
            task_type="context_compilation"
        )
        
        return critique
    
    async def _provide_gating_feedback(self,
                                     query: str,
                                     results: List[RetrievalResult],
                                     critique: Any):
        """
        Provide critique feedback to the similarity gate.
        
        Args:
            query: Original query
            results: Retrieval results
            critique: Context critique
        """
        # Convert critique to feedback format
        chunk_ids = [r.chunk_id for r in results if r.included]
        useful = []
        
        for chunk_id in chunk_ids:
            relevance = critique.relevance_scores.get(chunk_id, 0.5)
            useful.append(relevance > 0.5)
        
        feedback = {
            "chunk_ids": chunk_ids,
            "useful": useful,
            "unnecessary_chunks": critique.unnecessary_chunks,
            "missing_context": "; ".join(critique.blindspots[:3]) if critique.blindspots else None
        }
        
        # Record feedback
        self.similarity_gate.record_feedback(
            project_id=self.context_graph.project_id,
            retrieval_type="context_graph",
            feedback=feedback
        )
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        # Check cache
        cache_key = f"text:{hash(text)}"
        if cache_key in self.embedding_cache:
            self.retrieval_stats["cache_hits"] += 1
            return self.embedding_cache[cache_key]
        
        if not self.rag_client or not hasattr(self.rag_client, 'get_embedding'):
            return None
        
        try:
            embedding = await self.rag_client.get_embedding(text)
            self.embedding_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
            return None
    
    async def _get_node_embedding(self, node: MessageNode) -> Optional[List[float]]:
        """Get embedding for a message node."""
        # Check cache
        cache_key = f"node:{node.id}"
        if cache_key in self.embedding_cache:
            self.retrieval_stats["cache_hits"] += 1
            return self.embedding_cache[cache_key]
        
        # Use summary if available for efficiency
        text = node.summary if node.summary else node.content
        embedding = await self._get_embedding(text)
        
        if embedding:
            self.embedding_cache[cache_key] = embedding
            
        return embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
            
        return float(dot_product / norm_product)
    
    def _resolution_priority(self, resolution: ResolutionLevel) -> int:
        """Get priority value for resolution level."""
        priorities = {
            ResolutionLevel.FULL: 3,
            ResolutionLevel.SUMMARY: 2,
            ResolutionLevel.TITLE: 1,
            ResolutionLevel.HIDDEN: 0
        }
        return priorities.get(resolution, 0)
    
    async def analyze_retrieval_patterns(self, 
                                       project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze retrieval patterns for insights.
        
        Args:
            project_id: Specific project or None for all
            
        Returns:
            Analysis results
        """
        # Get statistics from similarity gate
        gate_stats = self.similarity_gate.get_statistics(
            project_id or self.context_graph.project_id
        )
        
        # Get critique summary
        critic_summary = self.quality_critic.get_critique_summary()
        
        # Combine with local stats
        analysis = {
            "retrieval_stats": self.retrieval_stats,
            "gating_stats": gate_stats,
            "quality_summary": critic_summary,
            "recommendations": self._generate_recommendations(
                gate_stats,
                critic_summary
            )
        }
        
        return analysis
    
    def _generate_recommendations(self,
                                gate_stats: Dict[str, Any],
                                critic_summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on patterns."""
        recommendations = []
        
        # Check quality trends
        quality_trend = critic_summary.get("quality_trend", "stable")
        if quality_trend == "declining":
            recommendations.append(
                "Context quality is declining - consider adjusting retrieval parameters"
            )
        
        # Check gating effectiveness
        if gate_stats.get("statistics", {}).get("context_graph", {}).get("precision", 1.0) < 0.7:
            recommendations.append(
                "Low precision in context retrieval - too many irrelevant chunks"
            )
        
        # Check blindspot patterns
        avg_blindspots = critic_summary.get("avg_blindspots", 0)
        if avg_blindspots > 2:
            recommendations.append(
                f"Average {avg_blindspots:.1f} blindspots per retrieval - "
                "consider expanding search scope"
            )
        
        # Check threshold adaptation
        for retrieval_type, stats in gate_stats.get("statistics", {}).items():
            current_threshold = stats.get("current_threshold", 0.7)
            base_threshold = stats.get("base_threshold", 0.7)
            
            if abs(current_threshold - base_threshold) > 0.2:
                recommendations.append(
                    f"Large threshold adaptation for {retrieval_type} "
                    f"({base_threshold:.2f} → {current_threshold:.2f}) - "
                    "review retrieval quality"
                )
        
        return recommendations
    
    def clear_caches(self):
        """Clear embedding and other caches."""
        self.embedding_cache.clear()
        logger.info(f"Cleared {len(self.embedding_cache)} cached embeddings")