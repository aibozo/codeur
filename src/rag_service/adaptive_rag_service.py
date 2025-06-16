"""
Adaptive RAG Service with integrated similarity gating.

This module enhances the existing RAG service with adaptive similarity gating
and quality feedback mechanisms.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

from .service import RAGService
from .models import SearchResult, CodeChunk
from ..core.adaptive_similarity_gate import AdaptiveSimilarityGate, RetrievalResult
from ..core.context_quality_critic import ContextQualityCritic, ContextChunk

logger = logging.getLogger(__name__)


class AdaptiveRAGService(RAGService):
    """
    Enhanced RAG service with adaptive similarity gating.
    
    This extends the base RAGService with:
    - Adaptive similarity thresholding
    - Quality feedback integration
    - Project-specific learning
    - Blindspot detection
    """
    
    def __init__(self,
                 persist_directory: Optional[str] = None,
                 repo_path: Optional[str] = None,
                 embedding_service: Optional[Any] = None,
                 similarity_gate: Optional[AdaptiveSimilarityGate] = None,
                 quality_critic: Optional[ContextQualityCritic] = None,
                 enable_adaptive_gating: bool = True):
        """
        Initialize the adaptive RAG service.
        
        Args:
            persist_directory: Directory for persistence
            repo_path: Repository root path
            embedding_service: Embedding service instance
            similarity_gate: Adaptive similarity gate (creates new if None)
            quality_critic: Quality critic (creates new if None)
            enable_adaptive_gating: Whether to enable adaptive features
        """
        # Initialize base service
        super().__init__(
            persist_directory=persist_directory,
            repo_path=repo_path
        )
        
        # Initialize adaptive components
        self.enable_adaptive_gating = enable_adaptive_gating
        
        if enable_adaptive_gating:
            self.similarity_gate = similarity_gate or AdaptiveSimilarityGate(
                profiles_dir=Path(persist_directory) / "similarity_profiles" if persist_directory else None
            )
            self.quality_critic = quality_critic or ContextQualityCritic()
        else:
            self.similarity_gate = None
            self.quality_critic = None
        
        # Track current project context
        self._current_project_id = None
        self._last_query = None
        self._last_results = None
        
        logger.info(f"Initialized Adaptive RAG Service (gating: {enable_adaptive_gating})")
    
    def search_code(self,
                   query: str,
                   k: int = 10,
                   filters: Optional[Dict[str, Any]] = None,
                   project_id: Optional[str] = None,
                   retrieval_type: str = "code_search") -> List[SearchResult]:
        """
        Enhanced search with adaptive similarity gating.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            project_id: Project identifier for adaptive thresholds
            retrieval_type: Type of retrieval for specialized handling
            
        Returns:
            List of filtered search results
        """
        # Get base search results
        raw_results = super().search_code(
            query=query,
            k=k * 2 if self.enable_adaptive_gating else k,  # Get more for filtering
            filters=filters
        )
        
        if not self.enable_adaptive_gating:
            return raw_results[:k]
        
        # Convert to format for similarity gate
        gating_input = []
        for result in raw_results:
            gating_input.append({
                "id": result.chunk.id,
                "content": result.chunk.content,
                "similarity": result.score,
                "metadata": {
                    "file_path": result.chunk.file_path,
                    "chunk_type": result.chunk.chunk_type,
                    "language": result.chunk.language,
                    "symbol_name": result.chunk.symbol_name
                }
            })
        
        # Apply adaptive gating
        project_id = project_id or self._get_project_id()
        gated_results = self.similarity_gate.filter_results(
            results=gating_input,
            project_id=project_id,
            retrieval_type=retrieval_type,
            target_chunks=k,
            min_chunks=min(3, k),
            max_chunks=k
        )
        
        # Filter and annotate results
        filtered_results = []
        result_map = {r.chunk.id: r for r in raw_results}
        
        for gated in gated_results:
            if gated.included and gated.chunk_id in result_map:
                original_result = result_map[gated.chunk_id]
                # Add gating metadata to the chunk's metadata
                if not hasattr(original_result.chunk, 'metadata') or original_result.chunk.metadata is None:
                    original_result.chunk.metadata = {}
                original_result.chunk.metadata["gating_reason"] = gated.reason
                original_result.chunk.metadata["adaptive_score"] = gated.similarity_score
                filtered_results.append(original_result)
        
        # Store for potential feedback
        self._last_query = query
        self._last_results = filtered_results
        self._current_project_id = project_id
        
        logger.debug(
            f"Adaptive search: {len(raw_results)} → {len(filtered_results)} results "
            f"(project: {project_id}, type: {retrieval_type})"
        )
        
        return filtered_results
    
    def get_context(self,
                   query: str,
                   k: int = 10,
                   max_tokens: int = 3000,
                   project_id: Optional[str] = None,
                   auto_critique: bool = True) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Enhanced context retrieval with quality analysis.
        
        Args:
            query: Context query
            k: Number of chunks
            max_tokens: Maximum tokens
            project_id: Project identifier
            auto_critique: Whether to run quality critique
            
        Returns:
            Tuple of (formatted context, critique summary)
        """
        # Get filtered results
        results = self.search_code(
            query=query,
            k=k,
            project_id=project_id,
            retrieval_type="context_retrieval"
        )
        
        if not results:
            return "No relevant context found.", None
        
        # Format context (same as base implementation)
        context_parts = []
        total_tokens = 0
        included_chunks = []
        
        for result in results:
            chunk = result.chunk
            
            # Format chunk
            chunk_text = f"""File: {chunk.file_path}:{chunk.start_line}-{chunk.end_line}
```{chunk.language}
{chunk.content}
```
"""
            
            # Check token count
            chunk_tokens = self.embedding_service.count_tokens(chunk_text)
            if total_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            total_tokens += chunk_tokens
            included_chunks.append(chunk)
        
        formatted_context = "\n".join(context_parts)
        
        # Run quality critique if enabled
        critique_summary = None
        if self.enable_adaptive_gating and auto_critique and self.quality_critic:
            # Run critique synchronously for now (can be made async later)
            critique_summary = self._critique_context_sync(
                query=query,
                chunks=included_chunks,
                project_id=project_id
            )
        
        return formatted_context, critique_summary
    
    def _critique_context_sync(self,
                               query: str,
                               chunks: List[CodeChunk],
                               project_id: str) -> Dict[str, Any]:
        """
        Run quality critique on retrieved context (synchronous version).
        
        Note: This is a simplified sync version. For async support,
        use asyncio.run() or integrate with async framework.
        
        Args:
            query: Original query
            chunks: Retrieved chunks
            project_id: Project identifier
            
        Returns:
            Critique summary
        """
        # For now, return a simplified critique
        # Full async version would use the quality critic
        
        summary = {
            "quality_score": 0.8,  # Default score
            "avg_relevance": 0.75,
            "blindspots": 0,
            "unnecessary_chunks": 0,
            "suggestions": []
        }
        
        # Basic heuristic analysis
        if len(chunks) < 3:
            summary["suggestions"].append("Consider lowering similarity threshold")
            summary["quality_score"] = 0.6
        elif len(chunks) > 8:
            summary["suggestions"].append("Too many chunks retrieved, consider raising threshold")
            summary["quality_score"] = 0.7
            
        return summary
    
    async def _critique_context(self,
                               query: str,
                               chunks: List[CodeChunk],
                               project_id: str) -> Dict[str, Any]:
        """
        Run quality critique on retrieved context (async version).
        
        Args:
            query: Original query
            chunks: Retrieved chunks
            project_id: Project identifier
            
        Returns:
            Critique summary
        """
        # Convert to critic format
        context_chunks = []
        for chunk in chunks:
            context_chunks.append(ContextChunk(
                chunk_id=chunk.id,
                content=chunk.content,
                similarity_score=0.7,  # Default, could get from result
                metadata={
                    "file_path": chunk.file_path,
                    "chunk_type": chunk.chunk_type,
                    "language": chunk.language
                }
            ))
        
        # Run critique
        critique = await self.quality_critic.critique_context(
            query=query,
            context_chunks=context_chunks,
            task_type="code"
        )
        
        # Provide feedback to similarity gate
        if self.similarity_gate and self._last_results:
            chunk_ids = [c.id for c in chunks]
            useful = [critique.relevance_scores.get(cid, 0.5) > 0.5 for cid in chunk_ids]
            
            feedback = {
                "chunk_ids": chunk_ids,
                "useful": useful,
                "unnecessary_chunks": critique.unnecessary_chunks,
                "missing_context": "; ".join(critique.blindspots[:3]) if critique.blindspots else None
            }
            
            self.similarity_gate.record_feedback(
                project_id=project_id,
                retrieval_type="context_retrieval",
                feedback=feedback
            )
        
        # Return summary
        return {
            "quality_score": critique.overall_quality,
            "avg_relevance": critique.metrics.get("avg_relevance", 0),
            "blindspots": len(critique.blindspots),
            "unnecessary_chunks": len(critique.unnecessary_chunks),
            "suggestions": critique.suggestions[:3]
        }
    
    def find_similar(self,
                    chunk: CodeChunk,
                    k: int = 10,
                    filters: Optional[Dict[str, Any]] = None,
                    project_id: Optional[str] = None) -> List[SearchResult]:
        """
        Find similar chunks with adaptive filtering.
        
        Args:
            chunk: Reference chunk
            k: Number of results
            filters: Optional filters
            project_id: Project identifier
            
        Returns:
            List of similar chunks
        """
        # Get base results
        raw_results = super().find_similar(
            chunk=chunk,
            k=k * 2 if self.enable_adaptive_gating else k,
            filters=filters
        )
        
        if not self.enable_adaptive_gating:
            return raw_results[:k]
        
        # Apply adaptive gating
        gating_input = []
        for result in raw_results:
            gating_input.append({
                "id": result.chunk.id,
                "content": result.chunk.content,
                "similarity": result.score,
                "metadata": {
                    "file_path": result.chunk.file_path,
                    "chunk_type": result.chunk.chunk_type
                }
            })
        
        project_id = project_id or self._get_project_id()
        gated_results = self.similarity_gate.filter_results(
            results=gating_input,
            project_id=project_id,
            retrieval_type="similarity_search",
            target_chunks=k,
            min_chunks=min(3, k),
            max_chunks=k
        )
        
        # Filter results
        filtered_results = []
        result_map = {r.chunk.id: r for r in raw_results}
        
        for gated in gated_results:
            if gated.included and gated.chunk_id in result_map:
                filtered_results.append(result_map[gated.chunk_id])
        
        return filtered_results
    
    def get_adaptive_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get adaptive gating statistics.
        
        Args:
            project_id: Project identifier (None for all)
            
        Returns:
            Statistics dictionary
        """
        if not self.enable_adaptive_gating:
            return {"enabled": False}
        
        stats = {
            "enabled": True,
            "gating_stats": self.similarity_gate.get_statistics(
                project_id or self._get_project_id()
            )
        }
        
        if self.quality_critic:
            stats["critique_summary"] = self.quality_critic.get_critique_summary()
        
        return stats
    
    def reset_adaptive_profile(self, project_id: Optional[str] = None):
        """
        Reset adaptive profile for a project.
        
        Args:
            project_id: Project to reset (None for current)
        """
        if not self.enable_adaptive_gating:
            return
        
        project_id = project_id or self._get_project_id()
        if project_id in self.similarity_gate.profiles:
            del self.similarity_gate.profiles[project_id]
            logger.info(f"Reset adaptive profile for project: {project_id}")
    
    def _get_project_id(self) -> str:
        """Get current project ID."""
        if self._current_project_id:
            return self._current_project_id
        
        # Use repo path as default project ID
        if self.repo_path:
            return Path(self.repo_path).name
        
        return "default"
    
    @classmethod
    def from_existing_service(cls,
                            existing_service: RAGService,
                            enable_adaptive_gating: bool = True) -> 'AdaptiveRAGService':
        """
        Create adaptive service from existing RAG service.
        
        Args:
            existing_service: Existing RAG service instance
            enable_adaptive_gating: Whether to enable adaptive features
            
        Returns:
            New adaptive RAG service
        """
        # Create new instance with same configuration
        adaptive_service = cls(
            persist_directory=str(existing_service.persist_dir) if existing_service.persist_dir else None,
            repo_path=str(existing_service.repo_path) if existing_service.repo_path else None,
            embedding_service=existing_service.embedding_service,
            enable_adaptive_gating=enable_adaptive_gating
        )
        
        # Copy internal state
        adaptive_service.vector_store = existing_service.vector_store
        adaptive_service.chunker = existing_service.chunker
        adaptive_service.search = existing_service.search
        adaptive_service.indexed_files = existing_service.indexed_files
        
        return adaptive_service