"""
Smart task batching for conflict-free parallel execution.

This module provides intelligent batching strategies that group tasks
to maximize parallelism while avoiding conflicts.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from src.architect.enhanced_task_graph import EnhancedTaskNode, TaskCommunity

logger = logging.getLogger(__name__)


@dataclass
class TaskBatch:
    """A batch of tasks that can be executed in parallel."""
    batch_id: str
    tasks: List[EnhancedTaskNode]
    reason: str  # Why these tasks are batched together
    estimated_duration: float = 0.0
    files_affected: Set[str] = None
    
    def __post_init__(self):
        if self.files_affected is None:
            self.files_affected = set()


class SmartTaskBatcher:
    """
    Intelligent task batching to maximize parallel execution.
    
    Strategies:
    1. Community-based: Tasks in same community likely work on same files
    2. File-based: Tasks affecting different files can run in parallel
    3. Test isolation: Test tasks can run after their related coding tasks
    4. Priority-based: High priority tasks in separate batches
    """
    
    def __init__(self, max_batch_size: int = 10):
        self.max_batch_size = max_batch_size
        
    def create_batches(self, 
                      tasks: List[EnhancedTaskNode],
                      communities: Dict[str, TaskCommunity] = None) -> List[TaskBatch]:
        """
        Create optimal batches from a list of tasks.
        
        Args:
            tasks: List of tasks to batch
            communities: Optional community information
            
        Returns:
            List of task batches
        """
        if not tasks:
            return []
            
        # Separate by type first
        coding_tasks = []
        test_tasks = []
        other_tasks = []
        
        for task in tasks:
            if task.agent_type == "test_agent" or task.metadata.get("is_test"):
                test_tasks.append(task)
            elif task.agent_type == "coding_agent":
                coding_tasks.append(task)
            else:
                other_tasks.append(task)
                
        batches = []
        
        # Batch coding tasks by community or files
        if communities:
            coding_batches = self._batch_by_community(coding_tasks, communities)
        else:
            coding_batches = self._batch_by_files(coding_tasks)
            
        batches.extend(coding_batches)
        
        # Batch test tasks separately (they depend on coding tasks)
        if test_tasks:
            test_batch = TaskBatch(
                batch_id=f"test_batch_{len(batches)}",
                tasks=test_tasks[:self.max_batch_size],
                reason="Test tasks (run after coding)"
            )
            batches.append(test_batch)
            
        # Add other tasks
        if other_tasks:
            other_batch = TaskBatch(
                batch_id=f"other_batch_{len(batches)}",
                tasks=other_tasks[:self.max_batch_size],
                reason="Miscellaneous tasks"
            )
            batches.append(other_batch)
            
        return batches
        
    def _batch_by_community(self, 
                          tasks: List[EnhancedTaskNode],
                          communities: Dict[str, TaskCommunity]) -> List[TaskBatch]:
        """Batch tasks by their community membership."""
        community_tasks = defaultdict(list)
        no_community_tasks = []
        
        # Group by community
        for task in tasks:
            if task.community_id and task.community_id in communities:
                community_tasks[task.community_id].append(task)
            else:
                no_community_tasks.append(task)
                
        batches = []
        
        # Create batch for each community
        for comm_id, comm_tasks in community_tasks.items():
            community = communities[comm_id]
            
            # Split large communities into multiple batches
            for i in range(0, len(comm_tasks), self.max_batch_size):
                batch_tasks = comm_tasks[i:i + self.max_batch_size]
                batch = TaskBatch(
                    batch_id=f"community_{comm_id}_{i//self.max_batch_size}",
                    tasks=batch_tasks,
                    reason=f"Community: {community.name or community.theme}",
                    files_affected=self._extract_files_from_tasks(batch_tasks)
                )
                batches.append(batch)
                
        # Batch remaining tasks by files
        if no_community_tasks:
            file_batches = self._batch_by_files(no_community_tasks)
            batches.extend(file_batches)
            
        return batches
        
    def _batch_by_files(self, tasks: List[EnhancedTaskNode]) -> List[TaskBatch]:
        """Batch tasks by files they affect to avoid conflicts."""
        file_groups = defaultdict(list)
        
        # Group tasks by primary file they affect
        for task in tasks:
            primary_file = self._get_primary_file(task)
            file_groups[primary_file].append(task)
            
        batches = []
        
        # Create batches from file groups
        # Tasks working on different files can run in parallel
        current_batch_files = set()
        current_batch_tasks = []
        
        for file_path, file_tasks in file_groups.items():
            # If adding these tasks would create conflicts, start new batch
            if file_path in current_batch_files or len(current_batch_tasks) >= self.max_batch_size:
                if current_batch_tasks:
                    batch = TaskBatch(
                        batch_id=f"file_batch_{len(batches)}",
                        tasks=current_batch_tasks,
                        reason="Tasks affecting different files",
                        files_affected=current_batch_files.copy()
                    )
                    batches.append(batch)
                    current_batch_tasks = []
                    current_batch_files = set()
                    
            # Add tasks to current batch
            current_batch_tasks.extend(file_tasks)
            current_batch_files.add(file_path)
            
        # Don't forget the last batch
        if current_batch_tasks:
            batch = TaskBatch(
                batch_id=f"file_batch_{len(batches)}",
                tasks=current_batch_tasks,
                reason="Tasks affecting different files",
                files_affected=current_batch_files
            )
            batches.append(batch)
            
        return batches
        
    def _get_primary_file(self, task: EnhancedTaskNode) -> str:
        """Extract the primary file a task will modify."""
        # Check metadata for file_path
        if task.metadata.get("file_path"):
            return task.metadata["file_path"]
            
        # Try to extract from title or description
        import re
        
        # Look for file paths in title/description
        text = f"{task.title} {task.description}"
        file_pattern = r'(?:src/|tests/|\./)[\w/]+\.(?:py|js|ts|jsx|tsx)'
        matches = re.findall(file_pattern, text)
        
        if matches:
            return matches[0]
            
        # Default to task ID to ensure uniqueness
        return f"unknown_{task.id}"
        
    def _extract_files_from_tasks(self, tasks: List[EnhancedTaskNode]) -> Set[str]:
        """Extract all files that will be affected by these tasks."""
        files = set()
        for task in tasks:
            primary_file = self._get_primary_file(task)
            if not primary_file.startswith("unknown_"):
                files.add(primary_file)
                
        return files
        
    def reorder_batches_by_priority(self, batches: List[TaskBatch]) -> List[TaskBatch]:
        """Reorder batches to execute high-priority tasks first."""
        def batch_priority(batch: TaskBatch) -> float:
            # Calculate average priority of tasks in batch
            if not batch.tasks:
                return 0.0
                
            priority_values = {
                "critical": 4.0,
                "high": 3.0,
                "medium": 2.0,
                "low": 1.0
            }
            
            total = sum(priority_values.get(task.priority.value, 2.0) for task in batch.tasks)
            return total / len(batch.tasks)
            
        # Sort batches by priority (highest first)
        return sorted(batches, key=batch_priority, reverse=True)