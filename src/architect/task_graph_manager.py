"""
Task Graph Manager - High-level interface for task graph operations.

This module provides a clean API for the Architect to create, manage, and
interact with enhanced task graphs, including RAG integration and scheduling.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .enhanced_task_graph import (
    EnhancedTaskGraph, EnhancedTaskNode, TaskCommunity,
    TaskPriority, TaskStatus, TaskGranularity, RAGContext, DisplayMode
)
from .community_detector import CommunityDetector
# Optional imports for scheduler and agent registry
try:
    from ..core.task_scheduler import TaskScheduler
    from ..core.agent_registry import AgentRegistry
    SCHEDULER_AVAILABLE = True
except ImportError:
    TaskScheduler = None
    AgentRegistry = None
    SCHEDULER_AVAILABLE = False

# Optional RAG integration
try:
    from ..rag_service import RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGClient = None
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TaskGraphContext:
    """Context for task graph operations."""
    project_id: str
    project_path: Path
    rag_client: Optional[Any] = None
    agent_registry: Optional[Any] = None
    scheduler: Optional[Any] = None
    event_publisher: Optional[Any] = None
    

class TaskGraphManager:
    """
    High-level manager for task graph operations.
    
    Provides:
    - Task graph creation and manipulation
    - Community detection and management
    - RAG context attachment
    - Scheduling integration
    - Persistence and loading
    """
    
    def __init__(self, context: TaskGraphContext):
        """
        Initialize the task graph manager.
        
        Args:
            context: Task graph context with project info and services
        """
        self.context = context
        self.graph = EnhancedTaskGraph(project_id=context.project_id)
        self.community_detector = CommunityDetector()
        
        # Storage path for persistence
        self.storage_path = context.project_path / ".architect" / "task_graphs"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    async def create_task_from_description(self,
                                         title: str,
                                         description: str,
                                         agent_type: str = "coding_agent",
                                         priority: TaskPriority = TaskPriority.MEDIUM,
                                         parent_id: Optional[str] = None,
                                         dependencies: Optional[Set[str]] = None) -> EnhancedTaskNode:
        """
        Create a task from natural language description.
        
        Automatically:
        - Detects granularity level
        - Attaches relevant RAG context
        - Assigns to community if applicable
        """
        # Determine granularity
        granularity = self._detect_granularity(title, description, parent_id)
        
        # Create task node
        task = EnhancedTaskNode(
            title=title,
            description=description,
            agent_type=agent_type,
            priority=priority,
            granularity=granularity,
            parent_id=parent_id,
            dependencies=dependencies or set()
        )
        
        # Add to graph
        self.graph.add_task(task)
        
        # Attach RAG context if available
        if self.context.rag_client and RAG_AVAILABLE:
            await self._attach_rag_context(task)
            
        # Auto-detect community for orphan tasks
        if not task.community_id and not parent_id:
            self._auto_assign_community(task)
            
        logger.info(f"Created task {task.id}: {task.title}")
        
        # Emit task created event if event publisher is available
        if self.context.event_publisher:
            event_data = {
                "task_id": task.id,
                "title": task.title,
                "description": task.description,
                "parent_id": task.parent_id,
                "status": task.status.value,
                "priority": task.priority.value,
                "agent_type": task.assigned_agent
            }
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self.context.event_publisher):
                    await self.context.event_publisher("task.created", event_data)
                else:
                    self.context.event_publisher("task.created", event_data)
            except Exception as e:
                logger.warning(f"Failed to emit task.created event: {e}")
        
        return task
        
    async def create_task_hierarchy(self,
                                  epic_title: str,
                                  epic_description: str,
                                  subtasks: List[Dict[str, Any]]) -> EnhancedTaskNode:
        """
        Create a complete task hierarchy with epic and subtasks.
        
        Args:
            epic_title: Title of the epic task
            epic_description: Description of the epic
            subtasks: List of subtask definitions
            
        Returns:
            The created epic task
        """
        # Create epic
        epic = await self.create_task_from_description(
            title=epic_title,
            description=epic_description,
            agent_type="architect",  # Epics managed by architect
            priority=TaskPriority.HIGH
        )
        # Set granularity after creation
        epic.granularity = TaskGranularity.EPIC
        
        # Create subtasks
        for subtask_def in subtasks:
            subtask = await self.create_task_from_description(
                title=subtask_def.get('title', ''),
                description=subtask_def.get('description', ''),
                agent_type=subtask_def.get('agent_type', 'coding_agent'),
                priority=TaskPriority[subtask_def.get('priority', 'MEDIUM').upper()],
                parent_id=epic.id,
                dependencies=set(subtask_def.get('dependencies', []))
            )
            
        return epic
        
    def detect_and_create_communities(self, method: str = "hybrid") -> List[TaskCommunity]:
        """
        Detect and create task communities.
        
        Args:
            method: Detection method to use
            
        Returns:
            List of created communities
        """
        communities = self.community_detector.detect_communities(self.graph, method)
        logger.info(f"Detected {len(communities)} communities using {method} method")
        return communities
        
    async def attach_rag_context_to_community(self, community_id: str, queries: List[str]):
        """
        Attach RAG context to all tasks in a community.
        
        Args:
            community_id: Community ID
            queries: Search queries for finding relevant context
        """
        if not self.context.rag_client or not RAG_AVAILABLE:
            return
            
        community = self.graph.communities.get(community_id)
        if not community:
            return
            
        # Search for relevant chunks
        all_chunks = []
        for query in queries:
            results = self.context.rag_client.search(query, k=5)
            all_chunks.extend([r['chunk_id'] for r in results if 'chunk_id' in r])
            
        # Attach to all tasks in community
        for task_id in community.task_ids:
            if task_id in self.graph.tasks:
                self.graph.attach_rag_context(task_id, all_chunks, queries)
                
        logger.info(f"Attached {len(all_chunks)} RAG chunks to community {community.name}")
        
    async def schedule_ready_tasks(self) -> int:
        """
        Schedule all ready tasks with the task scheduler.
        
        Returns:
            Number of tasks scheduled
        """
        if not self.context.scheduler:
            logger.warning("No scheduler available")
            return 0
            
        ready_tasks = self.graph.get_ready_tasks()
        scheduled = 0
        
        for task in ready_tasks:
            if isinstance(task, EnhancedTaskNode):
                await self.context.scheduler.schedule_task(task, self.graph)
                scheduled += 1
                
        logger.info(f"Scheduled {scheduled} ready tasks")
        return scheduled
        
    def get_abstracted_state(self) -> Dict[str, Any]:
        """
        Get abstracted graph state for architect context.
        
        Returns minimal information to avoid context bloat.
        """
        state = self.graph.get_abstracted_view()
        
        # Add scheduling info if available
        if self.context.scheduler:
            scheduler_status = self.context.scheduler.get_scheduler_status()
            state['scheduling'] = {
                'active_tasks': scheduler_status['active_tasks'],
                'queued_tasks': scheduler_status['queued_tasks']
            }
            
        return state
        
    def expand_task_context(self, task_id: str) -> Dict[str, Any]:
        """
        Get expanded context for a specific task.
        
        Used when focusing on a particular task.
        """
        if task_id not in self.graph.tasks:
            return {}
            
        task = self.graph.tasks[task_id]
        hierarchy = self.graph.get_task_hierarchy(task_id)
        
        context = {
            'task': task.to_dict(),
            'hierarchy': hierarchy,
            'community': None,
            'rag_context': {
                'chunks': task.rag_context.chunk_ids[:5],  # Limit chunks
                'queries': task.rag_context.search_queries
            }
        }
        
        # Add community info
        if task.community_id:
            community = self.graph.communities.get(task.community_id)
            if community:
                context['community'] = {
                    'name': community.name,
                    'theme': community.theme,
                    'related_tasks': len(community.task_ids)
                }
                
        return context
        
    def save_graph(self, filename: Optional[str] = None) -> Path:
        """
        Save the task graph to disk.
        
        Args:
            filename: Optional filename (defaults to project_id.json)
            
        Returns:
            Path to saved file
        """
        filename = filename or f"{self.context.project_id}.json"
        filepath = self.storage_path / filename
        
        # Serialize graph
        graph_data = {
            'project_id': self.graph.project_id,
            'tasks': {tid: task.to_dict() for tid, task in self.graph.tasks.items()},
            'communities': {
                cid: {
                    'id': comm.id,
                    'name': comm.name,
                    'description': comm.description,
                    'theme': comm.theme,
                    'color': comm.color,
                    'task_ids': list(comm.task_ids)
                }
                for cid, comm in self.graph.communities.items()
            },
            'display_state': {
                'display_mode': self.graph.display_mode.value,
                'focused_task_id': self.graph.focused_task_id,
                'expanded_task_ids': list(self.graph.expanded_task_ids)
            },
            'metadata': {
                'saved_at': datetime.utcnow().isoformat(),
                'task_count': len(self.graph.tasks),
                'community_count': len(self.graph.communities)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(graph_data, f, indent=2)
            
        logger.info(f"Saved task graph to {filepath}")
        return filepath
        
    def load_graph(self, filename: Optional[str] = None) -> bool:
        """
        Load a task graph from disk.
        
        Args:
            filename: Optional filename (defaults to project_id.json)
            
        Returns:
            True if loaded successfully
        """
        filename = filename or f"{self.context.project_id}.json"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            logger.warning(f"Graph file not found: {filepath}")
            return False
            
        try:
            with open(filepath, 'r') as f:
                graph_data = json.load(f)
                
            # Create new graph
            self.graph = EnhancedTaskGraph(project_id=graph_data['project_id'])
            
            # Recreate tasks
            for task_data in graph_data['tasks'].values():
                task = self._task_from_dict(task_data)
                self.graph.tasks[task.id] = task
                
                # Rebuild index structures
                if not task.dependencies:
                    self.graph.root_tasks.add(task.id)
                if task.status == TaskStatus.COMPLETED:
                    self.graph.completed_tasks.add(task.id)
                    
            # Recreate communities
            for comm_data in graph_data['communities'].values():
                community = TaskCommunity(
                    id=comm_data['id'],
                    name=comm_data['name'],
                    description=comm_data['description'],
                    theme=comm_data['theme'],
                    color=comm_data['color'],
                    task_ids=set(comm_data['task_ids'])
                )
                self.graph.communities[community.id] = community
                
            # Restore display state
            if 'display_state' in graph_data:
                state = graph_data['display_state']
                self.graph.display_mode = DisplayMode(state['display_mode'])
                self.graph.focused_task_id = state.get('focused_task_id')
                self.graph.expanded_task_ids = set(state.get('expanded_task_ids', []))
                
            logger.info(f"Loaded task graph from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            return False
            
    def _detect_granularity(self, title: str, description: str, parent_id: Optional[str]) -> TaskGranularity:
        """Detect task granularity based on content."""
        # If has parent, it's at least a subtask
        if parent_id:
            parent = self.graph.tasks.get(parent_id)
            if parent and parent.granularity == TaskGranularity.EPIC:
                return TaskGranularity.TASK
            else:
                return TaskGranularity.SUBTASK
                
        # Check for epic keywords
        epic_keywords = ['epic', 'feature', 'module', 'system', 'implement entire', 'build complete']
        if any(keyword in title.lower() or keyword in description.lower() for keyword in epic_keywords):
            return TaskGranularity.EPIC
            
        # Check for subtask keywords
        subtask_keywords = ['fix', 'update', 'change', 'modify', 'add button', 'update color']
        if any(keyword in title.lower() for keyword in subtask_keywords):
            return TaskGranularity.SUBTASK
            
        # Default to task
        return TaskGranularity.TASK
        
    async def _attach_rag_context(self, task: EnhancedTaskNode):
        """Attach relevant RAG context to a task."""
        # Search for relevant code
        query = f"{task.title} {task.description}"
        results = self.context.rag_client.search(query, k=10)
        
        # Extract chunk IDs
        chunk_ids = []
        
        # Extract file patterns and symbols
        file_patterns = set()
        symbols = set()
        
        for result in results:
            # Handle SearchResult objects
            if hasattr(result, 'chunk'):
                chunk_ids.append(result.chunk.id)
                if result.chunk.file_path:
                    file_patterns.add(result.chunk.file_path)
                if result.chunk.symbol_name:
                    symbols.add(result.chunk.symbol_name)
                
        # Update task context
        task.rag_context.chunk_ids = chunk_ids[:5]  # Limit to top 5
        task.rag_context.search_queries = [query]
        task.rag_context.file_patterns = list(file_patterns)[:3]
        task.rag_context.symbols = list(symbols)[:5]
        
    def _auto_assign_community(self, task: EnhancedTaskNode):
        """Auto-assign task to community based on similarity."""
        # Simple theme matching for now
        text = f"{task.title} {task.description}".lower()
        
        for community in self.graph.communities.values():
            # Check if task matches community theme
            if community.theme in text or any(
                keyword in text 
                for keyword in community.name.lower().split()
            ):
                task.community_id = community.id
                community.add_task(task.id)
                logger.info(f"Auto-assigned task {task.id} to community {community.name}")
                break
                
    def _task_from_dict(self, data: Dict[str, Any]) -> EnhancedTaskNode:
        """Recreate task from dictionary."""
        task = EnhancedTaskNode(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            agent_type=data['agent_type'],
            priority=TaskPriority(data['priority']),
            status=TaskStatus(data['status']),
            dependencies=set(data.get('dependencies', [])),
            dependents=set(data.get('dependents', [])),
            context=data.get('context', {}),
            parent_id=data.get('parent_id'),
            subtask_ids=set(data.get('subtask_ids', [])),
            granularity=TaskGranularity(data.get('granularity', 'task')),
            community_id=data.get('community_id'),
            estimated_hours=data.get('estimated_hours', 0.0),
            actual_hours=data.get('actual_hours', 0.0),
            expanded=data.get('expanded', False),
            hidden=data.get('hidden', False)
        )
        
        # Restore RAG context
        if 'rag_context' in data:
            rag = data['rag_context']
            task.rag_context.chunk_ids = rag.get('chunk_ids', [])
            task.rag_context.search_queries = rag.get('search_queries', [])
            task.rag_context.file_patterns = rag.get('file_patterns', [])
            task.rag_context.symbols = rag.get('symbols', [])
            
        # Restore timestamps
        if data.get('created_at'):
            task.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            task.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            task.completed_at = datetime.fromisoformat(data['completed_at'])
            
        return task