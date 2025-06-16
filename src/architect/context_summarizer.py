"""
Context-aware summarization for the context graph system.

This module provides specialized summarization for conversation nodes,
with awareness of conversation flow, importance, and context.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

from .context_graph import ContextGraph
from .context_graph_models import MessageNode, MessageCommunity, ResolutionConfig
from ..core.summarizer import SummarizationService, SummarizationResult
from ..core.logging import get_logger

logger = get_logger(__name__)


class ContextSummarizer:
    """
    Manages summarization for context graph nodes.
    
    This class handles:
    - Intelligent node selection for summarization
    - Batch processing for efficiency
    - Community summarization
    - Quality control and validation
    """
    
    def __init__(self,
                 graph: ContextGraph,
                 summarization_service: SummarizationService,
                 config: Optional[ResolutionConfig] = None):
        """
        Initialize the context summarizer.
        
        Args:
            graph: The context graph to summarize
            summarization_service: Service for generating summaries
            config: Resolution configuration
        """
        self.graph = graph
        self.summarizer = summarization_service
        self.config = config or graph.config
        
        # Track summarization state
        self._pending_nodes: Set[str] = set()
        self._summarizing = False
        self._last_summarization = datetime.now()
        
        logger.info("Initialized context summarizer")
        
    async def summarize_old_nodes(self, force: bool = False) -> Dict[str, Any]:
        """
        Summarize nodes that are old enough based on configuration.
        
        Args:
            force: Force summarization regardless of delay
            
        Returns:
            Summary of what was processed
        """
        # Check if enough time has passed
        if not force:
            time_since_last = (datetime.now() - self._last_summarization).total_seconds()
            if time_since_last < self.config.summarization_delay_seconds:
                logger.debug("Skipping summarization - too soon")
                return {"skipped": True, "reason": "delay"}
                
        # Find nodes that need summarization
        nodes_to_summarize = self._find_nodes_to_summarize()
        
        if not nodes_to_summarize:
            return {"processed": 0, "reason": "no_nodes"}
            
        # Check budget
        estimated_cost = await self._estimate_summarization_cost(nodes_to_summarize)
        if estimated_cost > self.config.daily_summarization_budget:
            logger.warning(f"Summarization would exceed budget: ${estimated_cost:.4f}")
            return {"skipped": True, "reason": "budget", "estimated_cost": estimated_cost}
            
        # Process in batches
        results = await self._summarize_nodes_batch(nodes_to_summarize)
        
        self._last_summarization = datetime.now()
        
        return {
            "processed": len(results),
            "successful": sum(1 for r in results if r.quality_score > 0.5),
            "total_cost": sum(r.cost for r in results),
            "avg_quality": sum(r.quality_score for r in results) / len(results) if results else 0
        }
        
    def _find_nodes_to_summarize(self) -> List[MessageNode]:
        """Find nodes that should be summarized."""
        nodes_to_summarize = []
        current_node_id = self.graph.current_node_id
        
        if not current_node_id:
            return nodes_to_summarize
            
        # Get distances from current node
        nodes_by_distance = self.graph.get_nodes_by_distance(
            current_node_id,
            max_distance=self.config.title_distance * 2
        )
        
        for distance, nodes in nodes_by_distance.items():
            for node in nodes:
                if self._should_summarize_node(node, distance):
                    nodes_to_summarize.append(node)
                    
        return nodes_to_summarize
        
    def _should_summarize_node(self, node: MessageNode, distance: int) -> bool:
        """Determine if a node should be summarized."""
        # Already has a summary
        if node.summary:
            return False
            
        # Too close to current conversation
        if distance <= self.config.full_context_distance:
            return False
            
        # Beyond summary distance threshold
        if distance > self.config.summary_distance:
            return True
            
        # Very important nodes might be preserved longer
        if node.importance_score >= self.config.importance_threshold:
            extended_distance = self.config.full_context_distance * 2
            if distance <= extended_distance:
                return False
                
        # In the summary range and not important - should be summarized
        return True
        
    async def _estimate_summarization_cost(self, nodes: List[MessageNode]) -> float:
        """Estimate the cost of summarizing the given nodes."""
        total_chars = sum(len(node.content) for node in nodes)
        avg_chars = total_chars / len(nodes) if nodes else 0
        
        return await self.summarizer.estimate_cost_for_nodes(
            node_count=len(nodes),
            avg_content_length=int(avg_chars),
            max_tokens=self.config.max_summary_tokens
        )
        
    async def _summarize_nodes_batch(self, nodes: List[MessageNode]) -> List[SummarizationResult]:
        """Summarize nodes in batches."""
        all_results = []
        
        # Process in configured batch sizes
        for i in range(0, len(nodes), self.config.batch_size):
            batch = nodes[i:i + self.config.batch_size]
            
            # Prepare content with context
            contents = []
            for node in batch:
                content_with_context = self._prepare_node_content(node)
                contents.append(content_with_context)
                
            # Summarize batch
            results = await self.summarizer.summarize_batch(
                contents,
                max_tokens=self.config.max_summary_tokens,
                preserve_code=self.config.preserve_code_blocks,
                preserve_decisions=self.config.preserve_decisions
            )
            
            # Update nodes with summaries
            for node, result in zip(batch, results):
                if result.quality_score >= self.config.min_summary_quality_score:
                    node.update_summary(result.summary, result.token_count)
                else:
                    logger.warning(f"Low quality summary for node {node.id[:8]}")
                    
            all_results.extend(results)
            
            # Small delay between batches
            if i + self.config.batch_size < len(nodes):
                await asyncio.sleep(0.5)
                
        return all_results
        
    def _prepare_node_content(self, node: MessageNode) -> str:
        """Prepare node content with context for better summarization."""
        parts = []
        
        # Add role and timestamp context
        parts.append(f"[{node.role.upper()} - {node.timestamp.strftime('%Y-%m-%d %H:%M')}]")
        
        # Add conversation phase if not exploration
        if node.conversation_phase.value != "exploration":
            parts.append(f"[Phase: {node.conversation_phase.value}]")
            
        # Add task context if available
        if node.primary_task_id:
            parts.append(f"[Task: {node.primary_task_id}]")
            
        # Add the actual content
        parts.append(node.content)
        
        # Add parent context if available and not too long
        if node.parent_id and node.parent_id in self.graph.nodes:
            parent = self.graph.nodes[node.parent_id]
            if parent.summary:
                parts.append(f"\n[Previous context: {parent.summary[:100]}...]")
            elif len(parent.content) < 200:
                parts.append(f"\n[Previous: {parent.content}]")
                
        return "\n".join(parts)
        
    async def summarize_community(self, community_id: str) -> Optional[str]:
        """
        Generate a summary for an entire community.
        
        Args:
            community_id: ID of the community to summarize
            
        Returns:
            The community summary, or None if failed
        """
        community = self.graph.communities.get(community_id)
        if not community:
            return None
            
        # Get all nodes in the community
        nodes = []
        for node_id in community.node_ids:
            if node_id in self.graph.nodes:
                nodes.append(self.graph.nodes[node_id])
                
        if not nodes:
            return None
            
        # Sort nodes chronologically
        nodes.sort(key=lambda n: n.timestamp)
        
        # Build community context
        content_parts = [
            f"Community: {community.name}",
            f"Theme: {community.theme}",
            f"Number of messages: {len(nodes)}",
            "\nConversation flow:"
        ]
        
        # Add node summaries or short content
        for node in nodes:
            if node.summary:
                content_parts.append(f"- {node.role}: {node.summary}")
            else:
                # Truncate long content
                content = node.content[:200] + "..." if len(node.content) > 200 else node.content
                content_parts.append(f"- {node.role}: {content}")
                
        full_content = "\n".join(content_parts)
        
        # Generate community summary
        result = await self.summarizer.summarize(
            full_content,
            max_tokens=self.config.max_community_summary_tokens,
            preserve_decisions=True,
            context=f"Summarize this conversation about {community.theme}"
        )
        
        if result.quality_score >= self.config.min_summary_quality_score:
            community.summary = result.summary
            community.last_updated = datetime.now()
            return result.summary
        else:
            logger.warning(f"Low quality community summary for {community.name}")
            return None
            
    async def create_incremental_summary(self, 
                                       node: MessageNode,
                                       new_context: List[MessageNode]) -> Optional[str]:
        """
        Create an incremental summary by updating existing summary with new context.
        
        Args:
            node: Node with existing summary to update
            new_context: New messages to incorporate
            
        Returns:
            Updated summary or None
        """
        if not node.summary:
            return None
            
        # Build update prompt
        update_parts = [
            f"Existing summary: {node.summary}",
            "\nNew context to incorporate:"
        ]
        
        for ctx_node in new_context:
            update_parts.append(f"- {ctx_node.role}: {ctx_node.content[:100]}...")
            
        update_content = "\n".join(update_parts)
        
        # Generate updated summary
        result = await self.summarizer.summarize(
            update_content,
            max_tokens=self.config.max_summary_tokens,
            context="Update the existing summary with the new context"
        )
        
        if result.quality_score >= self.config.min_summary_quality_score:
            return result.summary
        else:
            return None
            
    def get_summarization_stats(self) -> Dict[str, Any]:
        """Get statistics about summarization in the graph."""
        total_nodes = len(self.graph.nodes)
        summarized_nodes = sum(1 for n in self.graph.nodes.values() if n.summary)
        
        total_original_tokens = sum(n.token_count for n in self.graph.nodes.values())
        total_summary_tokens = sum(
            n.summary_token_count for n in self.graph.nodes.values() 
            if n.summary
        )
        
        communities_with_summaries = sum(
            1 for c in self.graph.communities.values() if c.summary
        )
        
        return {
            "total_nodes": total_nodes,
            "summarized_nodes": summarized_nodes,
            "summarization_rate": summarized_nodes / total_nodes if total_nodes > 0 else 0,
            "total_original_tokens": total_original_tokens,
            "total_summary_tokens": total_summary_tokens,
            "compression_ratio": (
                1 - (total_summary_tokens / total_original_tokens)
                if total_original_tokens > 0 else 0
            ),
            "communities_with_summaries": communities_with_summaries,
            "total_communities": len(self.graph.communities)
        }