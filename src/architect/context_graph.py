"""
Context Graph implementation for managing conversation history.

This module provides the core graph structure and operations for building
and navigating conversation context.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

from .context_graph_models import (
    MessageNode, MessageCommunity, ContextWindow,
    ResolutionLevel, ResolutionConfig, ConversationPhase,
    SemanticCheckpoint, PerformanceMetrics, BALANCED
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class ContextGraph:
    """
    Main context graph implementation for managing conversation history.
    
    This class provides:
    - Graph construction from messages
    - Distance-based traversal
    - Node relationship management
    - Community organization
    - Performance tracking
    """
    
    def __init__(self, project_id: str, config: ResolutionConfig = None):
        """
        Initialize a new context graph.
        
        Args:
            project_id: Unique identifier for the project
            config: Resolution configuration (uses BALANCED if not provided)
        """
        self.project_id = project_id
        self.config = config or BALANCED
        
        # Graph structure
        self.nodes: Dict[str, MessageNode] = {}
        self.current_node_id: Optional[str] = None
        self.root_nodes: Set[str] = set()
        
        # Communities
        self.communities: Dict[str, MessageCommunity] = {}
        
        # Checkpoints
        self.checkpoints: Dict[str, SemanticCheckpoint] = {}
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        
        # Caches
        self._distance_cache: Dict[Tuple[str, str], int] = {}
        self._path_cache: Dict[Tuple[str, str], List[str]] = {}
        
        logger.info(f"Initialized context graph for project {project_id}")
        
    async def add_message(self, 
                         role: str, 
                         content: str,
                         parent_id: Optional[str] = None,
                         task_ids: List[str] = None,
                         phase: ConversationPhase = ConversationPhase.EXPLORATION,
                         importance: float = 1.0,
                         **metadata) -> MessageNode:
        """
        Add a new message to the graph.
        
        Args:
            role: "user" or "assistant"
            content: The message content
            parent_id: ID of the parent message (None for root)
            task_ids: Associated task IDs
            phase: Current conversation phase
            importance: Importance score (0-1)
            **metadata: Additional metadata
            
        Returns:
            The created MessageNode
        """
        # Create the node
        node = MessageNode(
            role=role,
            content=content,
            parent_id=parent_id or self.current_node_id,
            conversation_phase=phase,
            importance_score=importance,
            token_count=self._estimate_tokens(content)
        )
        
        # Set task associations
        if task_ids:
            node.primary_task_id = task_ids[0]
            node.related_task_ids = task_ids[1:]
            
        # Add metadata
        if metadata:
            node.content_metadata.update(metadata)
            
        # Add to graph
        self.nodes[node.id] = node
        
        # Update relationships
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            parent.add_child(node.id)
        else:
            # This is a root node
            self.root_nodes.add(node.id)
            
        # Update current node
        self.current_node_id = node.id
        
        # Clear caches
        self._clear_caches()
        
        # Auto-create or update task-based communities
        if task_ids:
            await self._update_task_communities(node, task_ids)
        
        logger.debug(f"Added {role} message {node.id[:8]} to graph")
        
        return node
        
    def get_node(self, node_id: str) -> Optional[MessageNode]:
        """Get a node by ID."""
        node = self.nodes.get(node_id)
        if node:
            node.increment_access()
        return node
        
    def get_ancestors(self, node_id: str, max_depth: Optional[int] = None) -> List[MessageNode]:
        """
        Get all ancestors of a node (path from root to node).
        
        Args:
            node_id: The node to get ancestors for
            max_depth: Maximum depth to traverse (None for all)
            
        Returns:
            List of ancestors from root to parent
        """
        ancestors = []
        current_id = node_id
        depth = 0
        
        while current_id and (max_depth is None or depth < max_depth):
            node = self.nodes.get(current_id)
            if not node or not node.parent_id:
                break
                
            parent = self.nodes.get(node.parent_id)
            if parent:
                ancestors.append(parent)
                current_id = node.parent_id
                depth += 1
            else:
                break
                
        # Return in root-to-parent order
        ancestors.reverse()
        return ancestors
        
    def get_descendants(self, node_id: str, max_depth: Optional[int] = None) -> List[MessageNode]:
        """
        Get all descendants of a node.
        
        Args:
            node_id: The node to get descendants for
            max_depth: Maximum depth to traverse (None for all)
            
        Returns:
            List of all descendant nodes
        """
        descendants = []
        to_visit = [(node_id, 0)]
        
        while to_visit:
            current_id, depth = to_visit.pop(0)
            
            if max_depth is not None and depth > max_depth:
                continue
                
            node = self.nodes.get(current_id)
            if not node or current_id == node_id:
                if node and current_id != node_id:
                    descendants.append(node)
                    
                # Add children to visit
                if node:
                    for child_id in node.children_ids:
                        to_visit.append((child_id, depth + 1))
            else:
                descendants.append(node)
                
                # Add children to visit
                for child_id in node.children_ids:
                    to_visit.append((child_id, depth + 1))
                    
        return descendants
        
    def calculate_distance(self, from_node_id: str, to_node_id: str) -> int:
        """
        Calculate the distance between two nodes.
        
        Distance is the number of edges in the shortest path between nodes.
        
        Args:
            from_node_id: Starting node
            to_node_id: Target node
            
        Returns:
            Distance between nodes, or -1 if no path exists
        """
        # Check cache
        cache_key = (from_node_id, to_node_id)
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]
            
        # BFS to find shortest path
        if from_node_id == to_node_id:
            distance = 0
        else:
            visited = set()
            queue = [(from_node_id, 0)]
            distance = -1
            
            while queue:
                current_id, dist = queue.pop(0)
                
                if current_id == to_node_id:
                    distance = dist
                    break
                    
                if current_id in visited:
                    continue
                    
                visited.add(current_id)
                node = self.nodes.get(current_id)
                
                if node:
                    # Check parent
                    if node.parent_id and node.parent_id not in visited:
                        queue.append((node.parent_id, dist + 1))
                        
                    # Check children
                    for child_id in node.children_ids:
                        if child_id not in visited:
                            queue.append((child_id, dist + 1))
                            
        # Cache result
        self._distance_cache[cache_key] = distance
        return distance
        
    def get_conversation_path(self, node_id: str) -> List[MessageNode]:
        """
        Get the conversation path from root to the specified node.
        
        Args:
            node_id: Target node
            
        Returns:
            List of nodes from root to target
        """
        path = []
        current_id = node_id
        
        while current_id:
            node = self.nodes.get(current_id)
            if node:
                path.append(node)
                current_id = node.parent_id
            else:
                break
                
        # Return in chronological order
        path.reverse()
        return path
        
    def find_nearest_common_ancestor(self, node_id1: str, node_id2: str) -> Optional[str]:
        """
        Find the nearest common ancestor of two nodes.
        
        Args:
            node_id1: First node
            node_id2: Second node
            
        Returns:
            ID of the nearest common ancestor, or None
        """
        # Get ancestors of both nodes
        ancestors1 = set()
        current = node_id1
        
        while current:
            ancestors1.add(current)
            node = self.nodes.get(current)
            current = node.parent_id if node else None
            
        # Find first common ancestor
        current = node_id2
        while current:
            if current in ancestors1:
                return current
            node = self.nodes.get(current)
            current = node.parent_id if node else None
            
        return None
        
    def get_conversation_branch(self, node_id: str) -> List[MessageNode]:
        """
        Get all nodes in the same conversation branch.
        
        A branch includes ancestors and descendants.
        
        Args:
            node_id: Node to get branch for
            
        Returns:
            List of all nodes in the branch
        """
        branch_nodes = []
        
        # Add ancestors
        branch_nodes.extend(self.get_ancestors(node_id))
        
        # Add the node itself
        if node_id in self.nodes:
            branch_nodes.append(self.nodes[node_id])
            
        # Add descendants
        branch_nodes.extend(self.get_descendants(node_id))
        
        return branch_nodes
        
    def create_community(self, 
                        name: str,
                        theme: str,
                        node_ids: Set[str],
                        task_id: Optional[str] = None) -> MessageCommunity:
        """
        Create a new community of related messages.
        
        Args:
            name: Community name
            theme: Community theme/topic
            node_ids: Set of node IDs to include
            task_id: Associated task ID
            
        Returns:
            The created community
        """
        community = MessageCommunity(
            name=name,
            theme=theme,
            node_ids=node_ids,
            task_id=task_id
        )
        
        self.communities[community.id] = community
        
        # Update nodes with community membership
        for node_id in node_ids:
            if node_id in self.nodes:
                self.nodes[node_id].community_id = community.id
                
        logger.info(f"Created community '{name}' with {len(node_ids)} nodes")
        
        return community
        
    def add_checkpoint(self,
                      message_ids: List[str],
                      checkpoint_type: str,
                      title: str,
                      summary: str,
                      importance_reason: str) -> SemanticCheckpoint:
        """
        Create a semantic checkpoint for important conversation moments.
        
        Args:
            message_ids: Messages included in checkpoint
            checkpoint_type: Type of checkpoint
            title: Checkpoint title
            summary: Checkpoint summary
            importance_reason: Why this is important
            
        Returns:
            The created checkpoint
        """
        checkpoint = SemanticCheckpoint(
            message_ids=message_ids,
            checkpoint_type=checkpoint_type,
            title=title,
            summary=summary,
            importance_reason=importance_reason
        )
        
        self.checkpoints[checkpoint.id] = checkpoint
        
        logger.info(f"Created checkpoint '{title}' with {len(message_ids)} messages")
        
        return checkpoint
        
    def get_nodes_by_distance(self, from_node_id: str, max_distance: int) -> Dict[int, List[MessageNode]]:
        """
        Get all nodes grouped by distance from a given node.
        
        Args:
            from_node_id: Starting node
            max_distance: Maximum distance to search
            
        Returns:
            Dictionary mapping distance to list of nodes
        """
        nodes_by_distance: Dict[int, List[MessageNode]] = {}
        visited = set()
        queue = [(from_node_id, 0)]
        
        while queue:
            current_id, distance = queue.pop(0)
            
            if distance > max_distance or current_id in visited:
                continue
                
            visited.add(current_id)
            node = self.nodes.get(current_id)
            
            if node:
                if distance not in nodes_by_distance:
                    nodes_by_distance[distance] = []
                nodes_by_distance[distance].append(node)
                
                # Add neighbors
                if node.parent_id:
                    queue.append((node.parent_id, distance + 1))
                    
                for child_id in node.children_ids:
                    queue.append((child_id, distance + 1))
                    
        return nodes_by_distance
        
    def prune_old_branches(self, days: int = 30) -> int:
        """
        Prune old conversation branches that haven't been accessed recently.
        
        Args:
            days: Number of days to consider a branch old
            
        Returns:
            Number of nodes pruned
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        nodes_to_prune = set()
        
        # Find leaf nodes that haven't been accessed recently
        for node_id, node in self.nodes.items():
            if (not node.children_ids and  # Leaf node
                node.last_accessed and 
                node.last_accessed < cutoff_date and
                node.importance_score < self.config.importance_threshold):
                
                # Mark this branch for pruning
                current = node_id
                while current:
                    nodes_to_prune.add(current)
                    parent_node = self.nodes.get(current)
                    if parent_node and parent_node.children_ids:
                        # Stop if parent has other children
                        if len(parent_node.children_ids) > 1:
                            break
                    current = parent_node.parent_id if parent_node else None
                    
        # Remove pruned nodes
        for node_id in nodes_to_prune:
            del self.nodes[node_id]
            self.root_nodes.discard(node_id)
            
        # Clear caches
        self._clear_caches()
        
        logger.info(f"Pruned {len(nodes_to_prune)} old nodes")
        
        return len(nodes_to_prune)
        
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimate: 1 token per 4 characters
        return len(text) // 4
        
    async def _update_task_communities(self, node: MessageNode, task_ids: List[str]):
        """Auto-create or update communities based on task associations."""
        for task_id in task_ids:
            community_id = f"task_community_{task_id}"
            
            # Check if task community exists
            if community_id not in self.communities:
                # Create new task-based community
                community = MessageCommunity(
                    id=community_id,
                    name=f"Task {task_id} Discussion",
                    theme=f"task_{task_id}",
                    task_id=task_id
                )
                self.communities[community_id] = community
                logger.info(f"Created task-based community for {task_id}")
            
            # Add node to community
            community = self.communities[community_id]
            community.add_node(node.id)
            
            # Update node's community membership
            # Primary task gets primary community membership
            if task_id == node.primary_task_id:
                node.community_id = community_id
                
    def get_task_community(self, task_id: str) -> Optional[MessageCommunity]:
        """Get the community associated with a specific task."""
        community_id = f"task_community_{task_id}"
        return self.communities.get(community_id)
        
    def get_task_messages(self, task_id: str) -> List[MessageNode]:
        """Get all messages associated with a specific task."""
        messages = []
        for node in self.nodes.values():
            if (node.primary_task_id == task_id or 
                task_id in node.related_task_ids):
                messages.append(node)
        
        # Sort by timestamp
        messages.sort(key=lambda n: n.timestamp)
        return messages
    
    def _clear_caches(self):
        """Clear internal caches."""
        self._distance_cache.clear()
        self._path_cache.clear()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization."""
        return {
            "project_id": self.project_id,
            "current_node_id": self.current_node_id,
            "nodes": {
                node_id: {
                    "id": node.id,
                    "timestamp": node.timestamp.isoformat(),
                    "role": node.role,
                    "content": node.content,
                    "summary": node.summary,
                    "parent_id": node.parent_id,
                    "children_ids": node.children_ids,
                    "task_ids": [node.primary_task_id] + node.related_task_ids if node.primary_task_id else [],
                    "importance_score": node.importance_score,
                    "conversation_phase": node.conversation_phase.value
                }
                for node_id, node in self.nodes.items()
            },
            "communities": {
                comm_id: {
                    "id": comm.id,
                    "name": comm.name,
                    "theme": comm.theme,
                    "node_ids": list(comm.node_ids),
                    "summary": comm.summary
                }
                for comm_id, comm in self.communities.items()
            },
            "metrics": {
                "total_nodes": len(self.nodes),
                "total_communities": len(self.communities),
                "avg_context_size": self.metrics.avg_context_size
            }
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: ResolutionConfig = None) -> 'ContextGraph':
        """Create graph from dictionary."""
        graph = cls(data["project_id"], config)
        
        # Restore nodes
        for node_data in data["nodes"].values():
            node = MessageNode(
                id=node_data["id"],
                timestamp=datetime.fromisoformat(node_data["timestamp"]),
                role=node_data["role"],
                content=node_data["content"],
                summary=node_data.get("summary"),
                parent_id=node_data.get("parent_id"),
                importance_score=node_data.get("importance_score", 1.0)
            )
            graph.nodes[node.id] = node
            
        # Restore relationships
        for node_data in data["nodes"].values():
            if node_data.get("children_ids"):
                graph.nodes[node_data["id"]].children_ids = node_data["children_ids"]
                
        # Restore communities
        for comm_data in data.get("communities", {}).values():
            community = MessageCommunity(
                id=comm_data["id"],
                name=comm_data["name"],
                theme=comm_data["theme"],
                node_ids=set(comm_data["node_ids"]),
                summary=comm_data.get("summary")
            )
            graph.communities[community.id] = community
            
        graph.current_node_id = data.get("current_node_id")
        
        return graph