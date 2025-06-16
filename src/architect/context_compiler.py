"""
Context compilation for optimized LLM context windows.

This module provides the context compiler that determines resolution levels
for nodes and assembles the final context for LLM consumption.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio

from .context_graph import ContextGraph
from .context_graph_models import (
    MessageNode, MessageCommunity, ContextWindow,
    ResolutionLevel, ResolutionConfig, SemanticCheckpoint
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class ResolutionStrategy(ABC):
    """Abstract base class for resolution strategies."""
    
    @abstractmethod
    def calculate_resolution(self, 
                           node: MessageNode, 
                           distance: int,
                           config: ResolutionConfig) -> ResolutionLevel:
        """Calculate the resolution level for a node."""
        pass


class DistanceBasedStrategy(ResolutionStrategy):
    """Simple distance-based resolution strategy."""
    
    def calculate_resolution(self, 
                           node: MessageNode, 
                           distance: int,
                           config: ResolutionConfig) -> ResolutionLevel:
        """Calculate resolution based on distance from current node."""
        if distance <= config.full_context_distance:
            return ResolutionLevel.FULL
        elif distance <= config.summary_distance:
            return ResolutionLevel.SUMMARY
        elif distance <= config.title_distance:
            return ResolutionLevel.TITLE
        else:
            return ResolutionLevel.HIDDEN


class ImportanceBasedStrategy(ResolutionStrategy):
    """Resolution strategy that considers node importance."""
    
    def calculate_resolution(self, 
                           node: MessageNode, 
                           distance: int,
                           config: ResolutionConfig) -> ResolutionLevel:
        """Calculate resolution considering importance scores."""
        # High importance nodes get better resolution
        if node.importance_score >= config.importance_threshold:
            if distance <= config.full_context_distance * 2:
                return ResolutionLevel.FULL
            elif distance <= config.summary_distance * 2:
                return ResolutionLevel.SUMMARY
            else:
                return ResolutionLevel.TITLE
                
        # Normal nodes use standard distance-based resolution
        if distance <= config.full_context_distance:
            return ResolutionLevel.FULL
        elif distance <= config.summary_distance:
            return ResolutionLevel.SUMMARY
        elif distance <= config.title_distance:
            return ResolutionLevel.TITLE
        else:
            return ResolutionLevel.HIDDEN


class CheckpointAwareStrategy(ResolutionStrategy):
    """Resolution strategy that preserves semantic checkpoints."""
    
    def __init__(self, checkpoints: Dict[str, SemanticCheckpoint]):
        self.checkpoints = checkpoints
        self.checkpoint_nodes: Set[str] = set()
        for checkpoint in checkpoints.values():
            self.checkpoint_nodes.update(checkpoint.message_ids)
            
    def calculate_resolution(self, 
                           node: MessageNode, 
                           distance: int,
                           config: ResolutionConfig) -> ResolutionLevel:
        """Calculate resolution preserving checkpoint context."""
        # Checkpoint nodes are always at least summarized
        if node.id in self.checkpoint_nodes:
            if distance <= config.summary_distance:
                return ResolutionLevel.FULL
            else:
                return ResolutionLevel.SUMMARY
                
        # Normal resolution for other nodes
        if distance <= config.full_context_distance:
            return ResolutionLevel.FULL
        elif distance <= config.summary_distance:
            return ResolutionLevel.SUMMARY
        elif distance <= config.title_distance:
            return ResolutionLevel.TITLE
        else:
            return ResolutionLevel.HIDDEN


class TokenBudgetStrategy(ResolutionStrategy):
    """Resolution strategy that respects token budgets."""
    
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.current_tokens = 0
        
    def calculate_resolution(self, 
                           node: MessageNode, 
                           distance: int,
                           config: ResolutionConfig) -> ResolutionLevel:
        """Calculate resolution within token budget."""
        # Estimate tokens for different resolutions
        full_tokens = node.token_count
        summary_tokens = node.summary_token_count if node.summary else config.max_summary_tokens
        title_tokens = config.max_title_tokens
        
        # Try to fit as much as possible within budget
        if self.current_tokens + full_tokens <= self.max_tokens:
            self.current_tokens += full_tokens
            return ResolutionLevel.FULL
        elif self.current_tokens + summary_tokens <= self.max_tokens and node.summary:
            self.current_tokens += summary_tokens
            return ResolutionLevel.SUMMARY
        elif self.current_tokens + title_tokens <= self.max_tokens:
            self.current_tokens += title_tokens
            return ResolutionLevel.TITLE
        else:
            return ResolutionLevel.HIDDEN


class ContextCompiler:
    """
    Compiles optimized context windows from the conversation graph.
    
    This class orchestrates the resolution strategies to create
    context windows that fit within token budgets while preserving
    the most important information.
    """
    
    def __init__(self, graph: ContextGraph):
        """
        Initialize the context compiler.
        
        Args:
            graph: The context graph to compile from
        """
        self.graph = graph
        self.config = graph.config
        
        # Default strategies
        self.strategies: List[ResolutionStrategy] = [
            DistanceBasedStrategy(),
            ImportanceBasedStrategy()
        ]
        
        # Add checkpoint strategy if checkpoints exist
        if graph.checkpoints:
            self.strategies.append(CheckpointAwareStrategy(graph.checkpoints))
            
        logger.info("Initialized context compiler")
        
    def add_strategy(self, strategy: ResolutionStrategy):
        """Add a resolution strategy."""
        self.strategies.append(strategy)
        
    async def compile_context(self,
                            current_node_id: str,
                            max_tokens: Optional[int] = None,
                            include_communities: bool = True,
                            include_branch_only: bool = False) -> ContextWindow:
        """
        Compile an optimized context window.
        
        Args:
            current_node_id: Current position in the graph
            max_tokens: Maximum tokens for context (uses config default if None)
            include_communities: Whether to include community summaries
            include_branch_only: Only include current conversation branch
            
        Returns:
            Compiled context window
        """
        start_time = datetime.now()
        max_tokens = max_tokens or self.config.target_context_size
        
        # Get nodes to include
        if include_branch_only:
            nodes = self._get_branch_nodes(current_node_id)
        else:
            nodes = self._get_relevant_nodes(current_node_id, max_tokens)
            
        # Calculate resolutions for each node
        resolution_map = await self._calculate_resolutions(
            nodes, 
            current_node_id,
            max_tokens
        )
        
        # Get relevant communities
        communities = []
        if include_communities:
            communities = self._get_relevant_communities(nodes)
            
        # Create context window
        window = ContextWindow(
            current_node_id=current_node_id,
            nodes=nodes,
            resolution_map=resolution_map,
            communities=communities
        )
        
        # Calculate metrics
        self._calculate_window_metrics(window)
        window.compilation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.debug(
            f"Compiled context: {window.total_tokens} tokens, "
            f"{window.full_nodes} full, {window.summary_nodes} summary, "
            f"{window.title_nodes} title, {window.hidden_nodes} hidden"
        )
        
        return window
        
    def _get_branch_nodes(self, current_node_id: str) -> List[MessageNode]:
        """Get all nodes in the current conversation branch."""
        return self.graph.get_conversation_branch(current_node_id)
        
    def _get_relevant_nodes(self, 
                          current_node_id: str, 
                          max_tokens: int) -> List[MessageNode]:
        """Get relevant nodes within token budget."""
        # Start with conversation path
        path_nodes = self.graph.get_conversation_path(current_node_id)
        
        # Get nodes by distance
        max_distance = self.config.title_distance * 2
        nodes_by_distance = self.graph.get_nodes_by_distance(
            current_node_id, 
            max_distance
        )
        
        # Combine and deduplicate
        all_nodes = []
        seen_ids = set()
        
        # Path nodes first (most important)
        for node in path_nodes:
            if node.id not in seen_ids:
                all_nodes.append(node)
                seen_ids.add(node.id)
                
        # Then by distance
        for distance in sorted(nodes_by_distance.keys()):
            for node in nodes_by_distance[distance]:
                if node.id not in seen_ids:
                    all_nodes.append(node)
                    seen_ids.add(node.id)
                    
        return all_nodes
        
    async def _calculate_resolutions(self,
                                   nodes: List[MessageNode],
                                   current_node_id: str,
                                   max_tokens: int) -> Dict[str, ResolutionLevel]:
        """Calculate resolution levels for nodes."""
        resolution_map = {}
        
        # Add token budget strategy
        budget_strategy = TokenBudgetStrategy(max_tokens)
        strategies = self.strategies + [budget_strategy]
        
        # Calculate resolution for each node
        for node in nodes:
            distance = self.graph.calculate_distance(current_node_id, node.id)
            
            # Get resolution from each strategy
            resolutions = []
            for strategy in strategies:
                resolution = strategy.calculate_resolution(
                    node, 
                    distance, 
                    self.config
                )
                resolutions.append(resolution)
                
            # Use the most restrictive resolution
            final_resolution = self._combine_resolutions(resolutions)
            resolution_map[node.id] = final_resolution
            
        return resolution_map
        
    def _combine_resolutions(self, resolutions: List[ResolutionLevel]) -> ResolutionLevel:
        """Combine multiple resolution recommendations."""
        # Priority order (most restrictive to least)
        priority = {
            ResolutionLevel.HIDDEN: 0,
            ResolutionLevel.TITLE: 1,
            ResolutionLevel.SUMMARY: 2,
            ResolutionLevel.FULL: 3
        }
        
        # Return the most restrictive resolution
        min_resolution = ResolutionLevel.FULL
        min_priority = priority[min_resolution]
        
        for resolution in resolutions:
            if priority[resolution] < min_priority:
                min_resolution = resolution
                min_priority = priority[resolution]
                
        return min_resolution
        
    def _get_relevant_communities(self, 
                                nodes: List[MessageNode]) -> List[MessageCommunity]:
        """Get communities relevant to the included nodes."""
        relevant_communities = []
        seen_community_ids = set()
        
        for node in nodes:
            if node.community_id and node.community_id not in seen_community_ids:
                community = self.graph.communities.get(node.community_id)
                if community and community.summary:
                    relevant_communities.append(community)
                    seen_community_ids.add(node.community_id)
                    
        return relevant_communities
        
    def _calculate_window_metrics(self, window: ContextWindow):
        """Calculate metrics for the context window."""
        window.total_tokens = 0
        window.full_nodes = 0
        window.summary_nodes = 0
        window.title_nodes = 0
        window.hidden_nodes = 0
        
        for node in window.nodes:
            resolution = window.resolution_map.get(node.id, ResolutionLevel.HIDDEN)
            
            if resolution == ResolutionLevel.FULL:
                window.full_nodes += 1
                window.total_tokens += node.token_count
            elif resolution == ResolutionLevel.SUMMARY:
                window.summary_nodes += 1
                if node.summary:
                    window.total_tokens += node.summary_token_count
                else:
                    window.total_tokens += self.config.max_summary_tokens
            elif resolution == ResolutionLevel.TITLE:
                window.title_nodes += 1
                window.total_tokens += self.config.max_title_tokens
            else:
                window.hidden_nodes += 1
                
        # Add community tokens
        for community in window.communities:
            if community.summary:
                window.total_tokens += len(community.summary) // 4
            else:
                window.total_tokens += self.config.max_community_summary_tokens
                
    async def compile_with_focus(self,
                               current_node_id: str,
                               focus_node_ids: List[str],
                               max_tokens: Optional[int] = None) -> ContextWindow:
        """
        Compile context with focus on specific nodes.
        
        Args:
            current_node_id: Current position
            focus_node_ids: Nodes to prioritize
            max_tokens: Token budget
            
        Returns:
            Context window with focused nodes prioritized
        """
        # Create custom strategy that prioritizes focus nodes
        class FocusStrategy(ResolutionStrategy):
            def __init__(self, focus_ids: Set[str]):
                self.focus_ids = focus_ids
                
            def calculate_resolution(self, node, distance, config):
                if node.id in self.focus_ids:
                    return ResolutionLevel.FULL
                # Use normal resolution for others
                return DistanceBasedStrategy().calculate_resolution(
                    node, distance, config
                )
                
        # Add focus strategy temporarily
        focus_strategy = FocusStrategy(set(focus_node_ids))
        self.strategies.append(focus_strategy)
        
        try:
            # Compile with focus
            window = await self.compile_context(
                current_node_id,
                max_tokens=max_tokens
            )
        finally:
            # Remove focus strategy
            self.strategies.remove(focus_strategy)
            
        return window
        
    def estimate_context_size(self, current_node_id: str) -> Dict[str, int]:
        """
        Estimate context size with different strategies.
        
        Returns:
            Dictionary with token estimates for different approaches
        """
        estimates = {}
        
        # Full context (everything as FULL)
        all_nodes = self._get_relevant_nodes(current_node_id, float('inf'))
        estimates['full_context'] = sum(n.token_count for n in all_nodes)
        
        # With summarization
        summary_tokens = 0
        for node in all_nodes:
            distance = self.graph.calculate_distance(current_node_id, node.id)
            if distance <= self.config.full_context_distance:
                summary_tokens += node.token_count
            elif distance <= self.config.summary_distance:
                summary_tokens += self.config.max_summary_tokens
            elif distance <= self.config.title_distance:
                summary_tokens += self.config.max_title_tokens
                
        estimates['with_summarization'] = summary_tokens
        
        # Branch only
        branch_nodes = self._get_branch_nodes(current_node_id)
        estimates['branch_only'] = sum(n.token_count for n in branch_nodes)
        
        return estimates