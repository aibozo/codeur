"""
Data models for the Architect agent.
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class TaskPriority(Enum):
    """Priority levels for tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(Enum):
    """Status of a task in the graph."""
    PENDING = "pending"
    READY = "ready"  # All dependencies met
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class TaskNode:
    """
    Represents a single task in the task graph.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    agent_type: str = ""  # Which agent should handle this
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: Set[str] = field(default_factory=set)  # Task IDs this depends on
    dependents: Set[str] = field(default_factory=set)  # Tasks that depend on this
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep_id in completed_tasks for dep_id in self.dependencies)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'agent_type': self.agent_type,
            'priority': self.priority.value,
            'status': self.status.value,
            'dependencies': list(self.dependencies),
            'dependents': list(self.dependents),
            'context': self.context,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message
        }


@dataclass
class TaskGraph:
    """
    Represents the entire task dependency graph for a project.
    """
    project_id: str
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    root_tasks: Set[str] = field(default_factory=set)  # Tasks with no dependencies
    completed_tasks: Set[str] = field(default_factory=set)
    
    def add_task(self, task: TaskNode) -> None:
        """Add a task to the graph."""
        self.tasks[task.id] = task
        
        # Update root tasks
        if not task.dependencies:
            self.root_tasks.add(task.id)
        else:
            self.root_tasks.discard(task.id)
        
        # Update dependents for all dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                self.tasks[dep_id].dependents.add(task.id)
    
    def get_ready_tasks(self) -> List[TaskNode]:
        """Get all tasks that are ready to be executed."""
        ready = []
        for task in self.tasks.values():
            if (task.status == TaskStatus.PENDING and 
                task.is_ready(self.completed_tasks)):
                ready.append(task)
        return sorted(ready, key=lambda t: t.priority.value)
    
    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].completed_at = datetime.utcnow()
            self.completed_tasks.add(task_id)
    
    def get_critical_path(self) -> List[str]:
        """Get the critical path through the task graph."""
        # Simplified critical path - just find longest dependency chain
        def get_path_length(task_id: str, memo: Dict[str, int]) -> int:
            if task_id in memo:
                return memo[task_id]
            
            task = self.tasks.get(task_id)
            if not task or not task.dependents:
                memo[task_id] = 1
                return 1
            
            max_length = 0
            for dep_id in task.dependents:
                length = get_path_length(dep_id, memo)
                max_length = max(max_length, length)
            
            memo[task_id] = max_length + 1
            return max_length + 1
        
        memo = {}
        max_length = 0
        start_task = None
        
        for task_id in self.root_tasks:
            length = get_path_length(task_id, memo)
            if length > max_length:
                max_length = length
                start_task = task_id
        
        # Build the actual path
        path = []
        if start_task:
            current = start_task
            path.append(current)
            while self.tasks[current].dependents:
                # Follow the longest path
                next_task = None
                max_remaining = 0
                for dep_id in self.tasks[current].dependents:
                    if memo.get(dep_id, 0) > max_remaining:
                        max_remaining = memo[dep_id]
                        next_task = dep_id
                if next_task:
                    path.append(next_task)
                    current = next_task
                else:
                    break
        
        return path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'project_id': self.project_id,
            'tasks': {tid: task.to_dict() for tid, task in self.tasks.items()},
            'root_tasks': list(self.root_tasks),
            'completed_tasks': list(self.completed_tasks),
            'stats': {
                'total_tasks': len(self.tasks),
                'completed': len(self.completed_tasks),
                'ready': len(self.get_ready_tasks()),
                'blocked': len([t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED]),
                'critical_path_length': len(self.get_critical_path())
            }
        }


@dataclass
class ProjectStructure:
    """
    High-level project structure designed by the Architect.
    """
    components: List[Dict[str, Any]] = field(default_factory=list)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    data_flows: List[Dict[str, Any]] = field(default_factory=list)
    deployment_architecture: Optional[Dict[str, Any]] = None
    technology_stack: Dict[str, List[str]] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)