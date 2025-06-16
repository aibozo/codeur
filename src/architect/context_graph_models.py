"""
Data models for the Context Graph system.

This module defines the core structures for managing conversation context,
including message nodes, resolution levels, and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import uuid


class ResolutionLevel(Enum):
    """Context resolution levels for message nodes."""
    FULL = "full"  # Complete original message
    SUMMARY = "summary"  # AI-generated summary
    TITLE = "title"  # One-line description
    HIDDEN = "hidden"  # Not included in context


class ConversationPhase(Enum):
    """Phase of conversation for better context understanding."""
    EXPLORATION = "exploration"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    DEBUGGING = "debugging"


@dataclass
class ResolutionConfig:
    """Configurable thresholds for context resolution."""
    # Distance thresholds
    full_context_distance: int = 5
    summary_distance: int = 20
    title_distance: int = 50
    
    # Token limits
    max_full_tokens_per_node: int = 500
    max_summary_tokens: int = 100
    max_title_tokens: int = 20
    target_context_size: int = 8000
    
    # Community settings
    min_nodes_for_community: int = 5
    max_community_summary_tokens: int = 200
    community_inclusion_distance: int = 100
    community_detection_threshold: float = 0.7
    
    # Performance tuning
    batch_size: int = 10
    summarization_delay_seconds: int = 60
    cache_ttl_seconds: int = 3600
    parallel_workers: int = 3
    
    # Cost controls
    daily_summarization_budget: float = 1.0
    enable_embedding_generation: bool = True
    embedding_batch_size: int = 50
    cost_per_million_summary_tokens: float = 0.40
    cost_per_million_embedding_tokens: float = 0.10
    
    # Quality settings
    min_summary_quality_score: float = 0.8
    importance_threshold: float = 0.7
    preserve_code_blocks: bool = True
    preserve_decisions: bool = True
    
    def estimate_cost(self, num_messages: int, avg_message_length: int) -> float:
        """Estimate daily cost based on configuration."""
        total_tokens = num_messages * avg_message_length
        summary_tokens = total_tokens * (self.max_summary_tokens / avg_message_length)
        
        summary_cost = (summary_tokens / 1_000_000) * self.cost_per_million_summary_tokens
        embedding_cost = 0
        if self.enable_embedding_generation:
            embedding_cost = (summary_tokens / 1_000_000) * self.cost_per_million_embedding_tokens
            
        return summary_cost + embedding_cost


@dataclass
class MessageNode:
    """Represents a single message in the conversation graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    role: str = "user"  # "user" or "assistant"
    content: str = ""
    summary: Optional[str] = None
    embedding: Optional[List[float]] = None
    token_count: int = 0
    
    # Graph relationships
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    # Task association
    primary_task_id: Optional[str] = None
    related_task_ids: List[str] = field(default_factory=list)
    task_relevance_scores: Dict[str, float] = field(default_factory=dict)
    
    # Community membership
    community_id: Optional[str] = None
    
    # Conversation tracking
    conversation_phase: ConversationPhase = ConversationPhase.EXPLORATION
    
    # Metadata
    importance_score: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Summary metadata
    summary_version: int = 0
    last_summarized: Optional[datetime] = None
    summary_token_count: int = 0
    
    # Content type support
    content_type: str = "text"  # text, code, image, diagram
    content_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_child(self, child_id: str):
        """Add a child node."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)
            
    def increment_access(self):
        """Track access to this node."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        
    def update_summary(self, summary: str, token_count: int):
        """Update the summary for this node."""
        self.summary = summary
        self.summary_token_count = token_count
        self.summary_version += 1
        self.last_summarized = datetime.now()


@dataclass
class MessageCommunity:
    """Groups of related messages that can be summarized together."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    theme: str = ""
    node_ids: Set[str] = field(default_factory=set)
    
    # Summaries at different levels
    summary: Optional[str] = None
    detailed_summary: Optional[str] = None
    
    # Task association
    task_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: Optional[datetime] = None
    importance_score: float = 1.0
    
    # Hierarchy
    parent_community_id: Optional[str] = None
    sub_community_ids: Set[str] = field(default_factory=set)
    
    def add_node(self, node_id: str):
        """Add a node to the community."""
        self.node_ids.add(node_id)
        self.last_updated = datetime.now()
        
    def remove_node(self, node_id: str):
        """Remove a node from the community."""
        self.node_ids.discard(node_id)
        self.last_updated = datetime.now()
        
    def merge_with(self, other: 'MessageCommunity'):
        """Merge another community into this one."""
        self.node_ids.update(other.node_ids)
        self.sub_community_ids.add(other.id)
        self.last_updated = datetime.now()


@dataclass
class ContextWindow:
    """Represents the compiled context for a specific position in the graph."""
    current_node_id: str
    nodes: List[MessageNode]
    resolution_map: Dict[str, ResolutionLevel]
    communities: List[MessageCommunity]
    
    # Metrics
    total_tokens: int = 0
    full_nodes: int = 0
    summary_nodes: int = 0
    title_nodes: int = 0
    hidden_nodes: int = 0
    
    # Metadata
    compilation_time_ms: float = 0.0
    quality_score: float = 1.0
    
    def get_formatted_context(self) -> str:
        """Format the context window for LLM consumption."""
        parts = []
        
        for node in self.nodes:
            resolution = self.resolution_map.get(node.id, ResolutionLevel.HIDDEN)
            
            if resolution == ResolutionLevel.FULL:
                parts.append(f"[{node.timestamp.strftime('%Y-%m-%d %H:%M')}] {node.role}: {node.content}")
            elif resolution == ResolutionLevel.SUMMARY:
                parts.append(f"[{node.timestamp.strftime('%Y-%m-%d %H:%M')}] {node.role} (summary): {node.summary}")
            elif resolution == ResolutionLevel.TITLE:
                # Generate title from summary or content
                title = node.summary[:50] + "..." if node.summary else node.content[:50] + "..."
                parts.append(f"[{node.timestamp.strftime('%Y-%m-%d')}] {node.role}: {title}")
                
        return "\n\n".join(parts)


@dataclass
class SemanticCheckpoint:
    """Major conversation milestones that should be preserved."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_ids: List[str] = field(default_factory=list)
    checkpoint_type: str = "milestone"  # milestone, decision, pivot, completion
    title: str = ""
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    preserve_full_context: bool = True
    
    # Why this checkpoint matters
    importance_reason: str = ""
    
    # Related entities
    related_task_ids: List[str] = field(default_factory=list)
    related_decision_ids: List[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Metrics for monitoring context graph performance."""
    avg_context_size: int = 0
    avg_response_time: float = 0.0
    context_quality_score: float = 1.0
    daily_api_calls: int = 0
    daily_tokens_processed: int = 0
    cache_hit_rate: float = 0.0
    
    # Cost tracking
    daily_summarization_cost: float = 0.0
    daily_embedding_cost: float = 0.0
    
    # Quality metrics
    summary_quality_scores: List[float] = field(default_factory=list)
    context_utilization_rate: float = 0.0
    user_satisfaction_signals: List[bool] = field(default_factory=list)
    
    def calculate_daily_cost(self) -> float:
        """Calculate total daily cost."""
        return self.daily_summarization_cost + self.daily_embedding_cost
        
    def get_average_quality(self) -> float:
        """Get average summary quality score."""
        if not self.summary_quality_scores:
            return 1.0
        return sum(self.summary_quality_scores) / len(self.summary_quality_scores)


# Preset configurations
AGGRESSIVE_COMPRESSION = ResolutionConfig(
    full_context_distance=3,
    summary_distance=10,
    title_distance=25,
    max_summary_tokens=50,
    daily_summarization_budget=0.25
)

BALANCED = ResolutionConfig()  # Uses defaults

CONTEXT_RICH = ResolutionConfig(
    full_context_distance=10,
    summary_distance=40,
    title_distance=100,
    max_summary_tokens=150,
    daily_summarization_budget=2.0
)

DEVELOPMENT = ResolutionConfig(
    full_context_distance=20,
    summary_distance=50,
    max_summary_tokens=200,
    enable_embedding_generation=False,
    daily_summarization_budget=0.10
)