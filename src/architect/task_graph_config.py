"""
Configuration and setup for enhanced task graph system.

This module provides easy integration points for the enhanced task graph
with the existing agent architecture.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

from .enhanced_task_graph import EnhancedTaskGraph, DisplayMode
from .task_graph_manager import TaskGraphManager, TaskGraphContext
from .task_scheduler import IntelligentTaskScheduler
from .community_detector import CommunityDetector
from .llm_tools import ArchitectTools
from ..core.event_bridge import EventBridge
from ..core.agent_registry import AgentRegistry
from ..core.settings import Settings

logger = logging.getLogger(__name__)


class TaskGraphConfig:
    """Configuration for the enhanced task graph system."""
    
    def __init__(self,
                 project_path: Path,
                 event_bridge: EventBridge,
                 agent_registry: AgentRegistry,
                 settings: Settings,
                 rag_client: Optional[Any] = None):
        """
        Initialize task graph configuration.
        
        Args:
            project_path: Path to the project
            event_bridge: Event system for task notifications
            agent_registry: Registry of available agents
            settings: System settings
            rag_client: Optional RAG client for context attachment
        """
        self.project_path = project_path
        self.event_bridge = event_bridge
        self.agent_registry = agent_registry
        self.settings = settings
        self.rag_client = rag_client
        
        # Create components
        self.context = self._create_context()
        self.manager = self._create_manager()
        self.scheduler = self._create_scheduler()
        self.detector = self._create_detector()
        self.tools = self._create_tools()
        
    def _create_context(self) -> TaskGraphContext:
        """Create task graph context."""
        return TaskGraphContext(
            project_id=f"project_{self.project_path.name}",
            project_path=self.project_path,
            rag_client=self.rag_client,
            event_bridge=self.event_bridge
        )
        
    def _create_manager(self) -> TaskGraphManager:
        """Create task graph manager."""
        return TaskGraphManager(self.context)
        
    def _create_scheduler(self) -> IntelligentTaskScheduler:
        """Create intelligent task scheduler."""
        return IntelligentTaskScheduler(
            graph=self.manager.graph,
            agent_registry=self.agent_registry
        )
        
    def _create_detector(self) -> CommunityDetector:
        """Create community detector."""
        return CommunityDetector()
        
    def _create_tools(self) -> ArchitectTools:
        """Create LLM tools for architect."""
        return ArchitectTools(self.manager)
        
    def get_default_display_config(self) -> Dict[str, Any]:
        """Get default display configuration."""
        return {
            "default_mode": DisplayMode.SPARSE,
            "max_depth": 3,
            "show_completed": False,
            "community_colors": {
                "Authentication & Security": "#DC2626",
                "Database & Models": "#2563EB", 
                "API & Backend": "#059669",
                "Frontend & UI": "#7C3AED",
                "Testing & QA": "#EA580C",
                "DevOps & Infrastructure": "#0891B2",
                "Documentation": "#84CC16"
            }
        }
        
    def get_task_event_types(self) -> Dict[str, str]:
        """Get task-related event types."""
        return {
            "task_created": "task.created",
            "task_updated": "task.updated",
            "task_completed": "task.completed",
            "task_failed": "task.failed",
            "task_assigned": "task.assigned",
            "task_progress": "task.progress",
            "community_created": "community.created",
            "rag_attached": "task.rag_attached"
        }
        
    def register_event_handlers(self):
        """Register default event handlers for task events."""
        event_types = self.get_task_event_types()
        
        # Register task completion handler
        self.event_bridge.subscribe(
            event_types["task_completed"],
            self._handle_task_completed
        )
        
        # Register task assignment handler
        self.event_bridge.subscribe(
            event_types["task_assigned"],
            self._handle_task_assigned
        )
        
        logger.info("Registered task graph event handlers")
        
    async def _handle_task_completed(self, event: Dict[str, Any]):
        """Handle task completion events."""
        task_id = event.get("task_id")
        if task_id:
            # Update graph and check for newly ready tasks
            ready_tasks = self.manager.graph.get_ready_tasks()
            
            # Emit event for ready tasks
            if ready_tasks:
                await self.event_bridge.emit({
                    "type": "tasks.ready",
                    "tasks": [t.id for t in ready_tasks],
                    "count": len(ready_tasks)
                })
                
    async def _handle_task_assigned(self, event: Dict[str, Any]):
        """Handle task assignment events."""
        task_id = event.get("task_id")
        agent_id = event.get("agent_id")
        
        if task_id and agent_id:
            # Update task with assigned agent
            task = self.manager.graph.tasks.get(task_id)
            if task:
                task.assigned_agent = agent_id
                logger.info(f"Task {task_id} assigned to agent {agent_id}")
                
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return {
            "project_path": str(self.project_path),
            "project_id": self.context.project_id,
            "has_rag": self.rag_client is not None,
            "event_types": self.get_task_event_types(),
            "display_config": self.get_default_display_config(),
            "stats": {
                "total_tasks": len(self.manager.graph.tasks),
                "communities": len(self.manager.graph.communities),
                "ready_tasks": len(self.manager.graph.get_ready_tasks())
            }
        }


class TaskGraphIntegration:
    """
    Helper class for integrating task graph with existing agents.
    """
    
    @staticmethod
    def setup_architect_with_task_graph(architect, task_config: TaskGraphConfig):
        """
        Enhance an existing architect with task graph capabilities.
        
        Args:
            architect: Existing Architect instance
            task_config: Task graph configuration
        """
        # Add task manager and tools
        architect.task_manager = task_config.manager
        architect.task_tools = task_config.tools
        architect.task_scheduler = task_config.scheduler
        
        # Extend system prompt
        original_prompt = architect.get_system_prompt()
        task_prompt = """

You have access to an enhanced task graph system. When planning projects:

1. Use create_tasks() to build task hierarchies
2. Tasks are automatically organized into communities
3. Use simple list format for easy task creation:
   ```
   Project Name:
     - Main task (priority, hours)
       - Subtask 1
       - Subtask 2 (needs: Main task)
   ```
4. Check task status with get_task_status()
5. Tasks will be automatically assigned to appropriate agents
"""
        architect.system_prompt = original_prompt + task_prompt
        
        # Add function definitions
        architect.available_functions.extend(
            task_config.tools.get_tool_definitions()
        )
        
        logger.info("Enhanced architect with task graph capabilities")
        
    @staticmethod
    def create_task_aware_agent(agent_class, task_config: TaskGraphConfig):
        """
        Create an agent that's aware of the task system.
        
        Args:
            agent_class: Agent class to enhance
            task_config: Task graph configuration
        """
        class TaskAwareAgent(agent_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.task_config = task_config
                
            async def on_task_assigned(self, task_id: str):
                """Called when a task is assigned to this agent."""
                task = self.task_config.manager.graph.tasks.get(task_id)
                if task:
                    # Get RAG context if available
                    context = task.rag_context
                    
                    # Process task
                    await self.process_task(task, context)
                    
            async def process_task(self, task, context):
                """Process an assigned task."""
                # Override in subclass
                pass
                
            async def report_task_progress(self, task_id: str, progress: float, message: str = ""):
                """Report progress on a task."""
                await self.task_config.event_bridge.emit({
                    "type": "task.progress",
                    "task_id": task_id,
                    "progress": progress,
                    "message": message,
                    "agent_id": self.id
                })
                
        return TaskAwareAgent