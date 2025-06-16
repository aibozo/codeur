"""
Enhanced Task Graph with subtasks, communities, and RAG integration.

This module extends the basic task graph to support hierarchical task organization,
intelligent grouping, and dynamic context attachment.
"""

from typing import List, Dict, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import logging
from collections import defaultdict

from .models import TaskPriority, TaskStatus, TaskNode as BaseTaskNode, TaskGraph as BaseTaskGraph

logger = logging.getLogger(__name__)


class TaskGranularity(Enum):
    """Granularity levels for tasks."""
    EPIC = "epic"  # Highest level - major feature
    TASK = "task"  # Standard task - can have subtasks
    SUBTASK = "subtask"  # Atomic unit of work
    

class DisplayMode(Enum):
    """Display modes for the task graph."""
    SPARSE = "sparse"  # Show only high-level tasks
    FOCUSED = "focused"  # Show current task + its subtasks
    DENSE = "dense"  # Show everything
    CUSTOM = "custom"  # User-defined filter


@dataclass
class RAGContext:
    """RAG context attached to a task."""
    chunk_ids: List[str] = field(default_factory=list)  # RAG chunk references
    embeddings: Optional[List[float]] = None  # Task embedding
    search_queries: List[str] = field(default_factory=list)  # Queries to find context
    file_patterns: List[str] = field(default_factory=list)  # Files to include
    symbols: List[str] = field(default_factory=list)  # Code symbols to track
    

@dataclass 
class TaskCommunity:
    """Groups related tasks together."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    task_ids: Set[str] = field(default_factory=set)
    parent_community_id: Optional[str] = None  # For hierarchical communities
    theme: str = ""  # e.g., "authentication", "database", "frontend"
    color: str = "#6B7280"  # For visualization
    
    def add_task(self, task_id: str):
        """Add a task to this community."""
        self.task_ids.add(task_id)
        
    def remove_task(self, task_id: str):
        """Remove a task from this community."""
        self.task_ids.discard(task_id)


@dataclass
class EnhancedTaskNode(BaseTaskNode):
    """
    Enhanced task node with subtasks, communities, and RAG support.
    """
    # Hierarchical structure
    parent_id: Optional[str] = None
    subtask_ids: Set[str] = field(default_factory=set)
    granularity: TaskGranularity = TaskGranularity.TASK
    
    # Community membership
    community_id: Optional[str] = None
    
    # RAG integration
    rag_context: RAGContext = field(default_factory=RAGContext)
    
    # Estimation and tracking
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    
    # Display control
    expanded: bool = False  # Whether subtasks are shown in UI
    hidden: bool = False  # For filtering
    
    # Agent assignment
    assigned_agent: Optional[str] = None
    
    def add_subtask(self, subtask_id: str):
        """Add a subtask to this task."""
        self.subtask_ids.add(subtask_id)
        
    def add_rag_chunk(self, chunk_id: str):
        """Add a RAG chunk reference."""
        if chunk_id not in self.rag_context.chunk_ids:
            self.rag_context.chunk_ids.append(chunk_id)
            
    def set_embedding(self, embedding: List[float]):
        """Set the task embedding for similarity search."""
        self.rag_context.embeddings = embedding
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including new fields."""
        base_dict = super().to_dict()
        base_dict.update({
            'parent_id': self.parent_id,
            'subtask_ids': list(self.subtask_ids),
            'granularity': self.granularity.value,
            'community_id': self.community_id,
            'rag_context': {
                'chunk_ids': self.rag_context.chunk_ids,
                'search_queries': self.rag_context.search_queries,
                'file_patterns': self.rag_context.file_patterns,
                'symbols': self.rag_context.symbols,
            },
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'expanded': self.expanded,
            'hidden': self.hidden,
            'assigned_agent': self.assigned_agent,
        })
        return base_dict


@dataclass
class EnhancedTaskGraph(BaseTaskGraph):
    """
    Enhanced task graph with communities, hierarchies, and display modes.
    """
    # Community management
    communities: Dict[str, TaskCommunity] = field(default_factory=dict)
    
    # Display state
    display_mode: DisplayMode = DisplayMode.SPARSE
    focused_task_id: Optional[str] = None
    expanded_task_ids: Set[str] = field(default_factory=set)
    
    # Override to use EnhancedTaskNode
    tasks: Dict[str, EnhancedTaskNode] = field(default_factory=dict)
    
    def add_task(self, task: EnhancedTaskNode) -> None:
        """Add an enhanced task to the graph."""
        super().add_task(task)
        
        # Handle parent-child relationships
        if task.parent_id and task.parent_id in self.tasks:
            parent = self.tasks[task.parent_id]
            parent.add_subtask(task.id)
            
        # Auto-assign to community if parent has one
        if task.parent_id and not task.community_id:
            parent = self.tasks.get(task.parent_id)
            if parent and parent.community_id:
                task.community_id = parent.community_id
                self.communities[parent.community_id].add_task(task.id)
                
    def create_community(self, name: str, theme: str, task_ids: Optional[Set[str]] = None) -> TaskCommunity:
        """Create a new community and optionally add tasks."""
        community = TaskCommunity(
            name=name,
            theme=theme,
            task_ids=task_ids or set()
        )
        self.communities[community.id] = community
        
        # Update tasks with community assignment
        for task_id in community.task_ids:
            if task_id in self.tasks:
                self.tasks[task_id].community_id = community.id
                
        return community
        
    def auto_detect_communities(self, method: str = "theme") -> List[TaskCommunity]:
        """
        Automatically detect and create communities based on task similarity.
        
        Args:
            method: "theme" for keyword-based, "embedding" for semantic similarity
            
        Returns:
            List of created communities
        """
        if method == "theme":
            return self._detect_theme_communities()
        elif method == "embedding":
            return self._detect_embedding_communities()
        else:
            raise ValueError(f"Unknown community detection method: {method}")
            
    def _detect_theme_communities(self) -> List[TaskCommunity]:
        """Detect communities based on common themes in task titles/descriptions."""
        # Common themes to look for
        themes = {
            "authentication": ["auth", "login", "user", "session", "jwt", "token"],
            "database": ["db", "database", "schema", "migration", "model", "query"],
            "api": ["api", "endpoint", "route", "rest", "graphql", "controller"],
            "frontend": ["ui", "component", "react", "vue", "style", "layout"],
            "testing": ["test", "spec", "unit", "integration", "coverage", "mock"],
            "deployment": ["deploy", "ci", "cd", "docker", "kubernetes", "build"],
        }
        
        created_communities = []
        theme_tasks = defaultdict(set)
        
        # Group tasks by detected themes
        for task_id, task in self.tasks.items():
            if task.community_id:  # Skip if already assigned
                continue
                
            text = f"{task.title} {task.description}".lower()
            
            for theme, keywords in themes.items():
                if any(keyword in text for keyword in keywords):
                    theme_tasks[theme].add(task_id)
                    break  # Assign to first matching theme
                    
        # Create communities for detected themes
        for theme, task_ids in theme_tasks.items():
            if len(task_ids) >= 2:  # Only create community if multiple tasks
                community = self.create_community(
                    name=f"{theme.title()} Tasks",
                    theme=theme,
                    task_ids=task_ids
                )
                created_communities.append(community)
                
        return created_communities
        
    def get_ready_tasks(self) -> List[EnhancedTaskNode]:
        """Get all tasks that are ready to be executed."""
        ready = []
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.READY]:
                # Check if all dependencies are completed
                deps_completed = all(
                    self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                    if dep_id in self.tasks
                )
                if deps_completed:
                    ready.append(task)
        return sorted(ready, key=lambda t: t.priority.value, reverse=True)
        
    def _detect_embedding_communities(self) -> List[TaskCommunity]:
        """Detect communities based on embedding similarity."""
        # This would use task embeddings to cluster similar tasks
        # Placeholder for now - would integrate with actual embedding service
        logger.warning("Embedding-based community detection not yet implemented")
        return []
        
    def get_display_tasks(self, mode: Optional[DisplayMode] = None) -> Dict[str, EnhancedTaskNode]:
        """
        Get tasks based on display mode.
        
        Args:
            mode: Display mode to use (defaults to graph's current mode)
            
        Returns:
            Dictionary of tasks to display
        """
        mode = mode or self.display_mode
        display_tasks = {}
        
        if mode == DisplayMode.DENSE:
            # Show everything
            display_tasks = {tid: task for tid, task in self.tasks.items() if not task.hidden}
            
        elif mode == DisplayMode.SPARSE:
            # Show only top-level tasks (no parents) and collapsed tasks
            for tid, task in self.tasks.items():
                if not task.hidden and (not task.parent_id or task.parent_id not in self.tasks):
                    display_tasks[tid] = task
                    
        elif mode == DisplayMode.FOCUSED:
            # Show focused task and its immediate children
            if self.focused_task_id and self.focused_task_id in self.tasks:
                focused = self.tasks[self.focused_task_id]
                display_tasks[self.focused_task_id] = focused
                
                # Add immediate children
                for subtask_id in focused.subtask_ids:
                    if subtask_id in self.tasks:
                        display_tasks[subtask_id] = self.tasks[subtask_id]
                        
                # Add parent for context
                if focused.parent_id and focused.parent_id in self.tasks:
                    display_tasks[focused.parent_id] = self.tasks[focused.parent_id]
                    
        # Handle expanded tasks in any mode
        for task_id in self.expanded_task_ids:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                display_tasks[task_id] = task
                # Add all subtasks of expanded tasks
                for subtask_id in task.subtask_ids:
                    if subtask_id in self.tasks:
                        display_tasks[subtask_id] = self.tasks[subtask_id]
                        
        return display_tasks
        
    def toggle_task_expansion(self, task_id: str) -> bool:
        """Toggle whether a task's subtasks are shown."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.expanded = not task.expanded
            
            if task.expanded:
                self.expanded_task_ids.add(task_id)
            else:
                self.expanded_task_ids.discard(task_id)
                
            return task.expanded
        return False
        
    def set_focused_task(self, task_id: Optional[str]):
        """Set the currently focused task."""
        if task_id is None or task_id in self.tasks:
            self.focused_task_id = task_id
            
    def get_community_tasks(self, community_id: str) -> List[EnhancedTaskNode]:
        """Get all tasks in a community."""
        if community_id not in self.communities:
            return []
            
        community = self.communities[community_id]
        return [self.tasks[tid] for tid in community.task_ids if tid in self.tasks]
        
    def get_task_hierarchy(self, task_id: str) -> Dict[str, Any]:
        """Get the full hierarchy for a task (ancestors and descendants)."""
        if task_id not in self.tasks:
            return {}
            
        task = self.tasks[task_id]
        hierarchy = {
            'task': task,
            'ancestors': [],
            'descendants': {}
        }
        
        # Get ancestors
        current = task
        while current.parent_id and current.parent_id in self.tasks:
            parent = self.tasks[current.parent_id]
            hierarchy['ancestors'].insert(0, parent)
            current = parent
            
        # Get descendants recursively
        def get_descendants(parent_id: str) -> Dict[str, Any]:
            parent = self.tasks[parent_id]
            desc = {}
            for child_id in parent.subtask_ids:
                if child_id in self.tasks:
                    child = self.tasks[child_id]
                    desc[child_id] = {
                        'task': child,
                        'subtasks': get_descendants(child_id) if child.subtask_ids else {}
                    }
            return desc
            
        hierarchy['descendants'] = get_descendants(task_id)
        return hierarchy
        
    def get_abstracted_view(self) -> Dict[str, Any]:
        """
        Get an abstracted view suitable for architect context.
        Shows communities and high-level task counts.
        """
        view = {
            'total_tasks': len(self.tasks),
            'completed_tasks': len(self.completed_tasks),
            'communities': {},
            'top_level_tasks': [],
            'critical_path': self.get_critical_path()[:5],  # First 5 tasks
        }
        
        # Community summaries
        for comm_id, community in self.communities.items():
            comm_tasks = [self.tasks[tid] for tid in community.task_ids if tid in self.tasks]
            view['communities'][comm_id] = {
                'name': community.name,
                'theme': community.theme,
                'task_count': len(comm_tasks),
                'completed_count': len([t for t in comm_tasks if t.status == TaskStatus.COMPLETED]),
                'active_task': next((t.title for t in comm_tasks if t.status == TaskStatus.IN_PROGRESS), None)
            }
            
        # Top-level task summaries
        for tid, task in self.tasks.items():
            if not task.parent_id and task.granularity != TaskGranularity.SUBTASK:
                view['top_level_tasks'].append({
                    'id': tid,
                    'title': task.title,
                    'status': task.status.value,
                    'subtask_count': len(task.subtask_ids),
                    'community': self.communities[task.community_id].name if task.community_id else None
                })
                
        return view
        
    def attach_rag_context(self, task_id: str, chunk_ids: List[str], 
                          queries: Optional[List[str]] = None):
        """Attach RAG context to a task."""
        if task_id not in self.tasks:
            return
            
        task = self.tasks[task_id]
        for chunk_id in chunk_ids:
            task.add_rag_chunk(chunk_id)
            
        if queries:
            task.rag_context.search_queries.extend(queries)
            
    def propagate_rag_context(self, task_id: str, direction: str = "down"):
        """
        Propagate RAG context from a task to its relatives.
        
        Args:
            task_id: Source task
            direction: "up" to parents, "down" to children, "both" for both
        """
        if task_id not in self.tasks:
            return
            
        source_task = self.tasks[task_id]
        context = source_task.rag_context
        
        if direction in ["down", "both"]:
            # Propagate to all descendants
            for child_id in source_task.subtask_ids:
                if child_id in self.tasks:
                    child = self.tasks[child_id]
                    # Merge contexts
                    for chunk_id in context.chunk_ids:
                        child.add_rag_chunk(chunk_id)
                    # Recursive propagation
                    self.propagate_rag_context(child_id, "down")
                    
        if direction in ["up", "both"] and source_task.parent_id:
            # Propagate summarized context to parent
            parent = self.tasks[source_task.parent_id]
            # Add a subset of most relevant chunks
            for chunk_id in context.chunk_ids[:3]:  # Top 3 chunks
                parent.add_rag_chunk(chunk_id)