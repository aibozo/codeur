"""
Base class for agents integrated with task graph and RAG systems.

This provides a standard foundation for all agents to access shared
infrastructure in a consistent way.
"""

import logging
from typing import Dict, Any, Optional, List, Set
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .agent_integration_interfaces import (
    TaskGraphIntegration, RAGIntegration, EventIntegration,
    AgentCapability, IntegrationLevel
)
from ..architect.task_graph_manager import TaskGraphManager, TaskGraphContext
from ..architect.enhanced_task_graph import (
    TaskStatus, TaskPriority, EnhancedTaskNode
)
from .event_bridge import EventBridge
from .simple_event_bridge import SimpleEventBridge
from .logging import get_logger

# Optional RAG import
try:
    from ..rag_service import RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGClient = None
    RAG_AVAILABLE = False

logger = get_logger(__name__)


@dataclass
class AgentContext:
    """Context shared by all integrated agents."""
    project_path: Path
    event_bridge: EventBridge
    task_manager: Optional[TaskGraphManager] = None
    rag_client: Optional[Any] = None
    agent_id: str = ""
    capabilities: Set[AgentCapability] = field(default_factory=set)
    simple_event_bridge: Optional[Any] = None
    

class IntegratedAgentBase(ABC):
    """
    Base class for agents with task graph and RAG integration.
    
    This provides standard implementations for common integration patterns
    while allowing agents to customize behavior as needed.
    """
    
    def __init__(self, context: AgentContext):
        """
        Initialize integrated agent.
        
        Args:
            context: Shared agent context with connections to infrastructure
        """
        self.context = context
        self.logger = get_logger(self.__class__.__name__)
        
        # Set up integrations
        self._task_integration = None
        self._rag_integration = None
        self._event_integration = None
        
        # Initialize integrations based on agent needs
        self._setup_integrations()
        
        # Subscribe to relevant events
        self._setup_event_subscriptions()
        
    @abstractmethod
    def get_integration_level(self) -> IntegrationLevel:
        """Get the level of integration this agent needs."""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> Set[AgentCapability]:
        """Get the capabilities this agent provides."""
        pass
        
    def _setup_integrations(self):
        """Set up integrations based on agent needs."""
        level = self.get_integration_level()
        
        # Task graph integration
        if level in [IntegrationLevel.FULL, IntegrationLevel.TASK_ONLY]:
            self._task_integration = TaskGraphIntegrationImpl(
                self.context.task_manager,
                self.context.agent_id
            )
            
        # RAG integration
        if level in [IntegrationLevel.FULL, IntegrationLevel.RAG_ONLY]:
            if RAG_AVAILABLE and self.context.rag_client:
                self._rag_integration = RAGIntegrationImpl(
                    self.context.rag_client,
                    self.context.agent_id
                )
            else:
                self.logger.warning("RAG requested but not available")
                
        # Event integration (all agents get this)
        # Create simple event bridge if not provided
        if not self.context.simple_event_bridge:
            self.context.simple_event_bridge = SimpleEventBridge(
                event_bridge=self.context.event_bridge
            )
            
        self._event_integration = EventIntegrationImpl(
            self.context.event_bridge,
            self.context.agent_id,
            self.context.simple_event_bridge
        )
        
    def _setup_event_subscriptions(self):
        """Subscribe to relevant events."""
        # Subscribe to task assignment events
        if self._task_integration and self.context.simple_event_bridge:
            self.context.simple_event_bridge.subscribe(
                "task.assigned",
                self._handle_task_assigned
            )
            
        # Subscribe to agent coordination events
        if self.context.simple_event_bridge:
            self.context.simple_event_bridge.subscribe(
                f"agent.{self.context.agent_id}.request",
                self._handle_agent_request
            )
        
    async def _handle_task_assigned(self, event: Dict[str, Any]):
        """Handle task assignment events."""
        if event.get("agent_id") == self.context.agent_id:
            task_id = event.get("task_id")
            if task_id:
                await self.on_task_assigned(task_id)
                
    async def _handle_agent_request(self, event: Dict[str, Any]):
        """Handle requests from other agents."""
        request_type = event.get("type")
        payload = event.get("payload", {})
        sender = event.get("sender_id")
        
        await self.on_agent_request(request_type, payload, sender)
        
    @abstractmethod
    async def on_task_assigned(self, task_id: str):
        """
        Called when a task is assigned to this agent.
        
        Args:
            task_id: ID of the assigned task
        """
        pass
        
    async def on_agent_request(self, request_type: str, payload: Dict[str, Any], sender_id: str):
        """
        Handle requests from other agents.
        
        Override this to handle specific request types.
        
        Args:
            request_type: Type of request
            payload: Request data
            sender_id: ID of requesting agent
        """
        self.logger.debug(f"Received request {request_type} from {sender_id}")
        
    # Task Graph Helpers
    
    async def get_current_task(self) -> Optional[EnhancedTaskNode]:
        """Get the current task assigned to this agent."""
        if not self._task_integration:
            return None
            
        # Find tasks assigned to this agent
        for task in self._task_integration.get_assigned_tasks():
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        return None
        
    async def update_task_progress(self, task_id: str, progress: float, message: str = ""):
        """Update progress on a task."""
        if self._task_integration:
            await self._task_integration.update_task_status(
                task_id,
                TaskStatus.IN_PROGRESS,
                {"progress": progress, "message": message}
            )
            
        # Emit progress event
        if self._event_integration:
            await self._event_integration.publish_event("task.progress", {
                "task_id": task_id,
                "agent_id": self.context.agent_id,
                "progress": progress,
                "message": message
            })
            
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark a task as completed."""
        if self._task_integration:
            await self._task_integration.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                {"result": result, "completed_by": self.context.agent_id}
            )
            
    async def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        if self._task_integration:
            await self._task_integration.update_task_status(
                task_id,
                TaskStatus.FAILED,
                {"error": error, "failed_by": self.context.agent_id}
            )
            
    # RAG Helpers
    
    async def search_context(self, query: str, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search RAG for relevant context."""
        if not self._rag_integration:
            return []
            
        # Add task context to query if available
        if task_id and self._task_integration:
            task = self._task_integration.get_task(task_id)
            if task:
                query = f"{task.title} {task.description} {query}"
                
        return await self._rag_integration.search_knowledge(
            query,
            filter_type="all"
        )
        
    async def store_implementation(self, 
                                 code: str, 
                                 description: str,
                                 task_id: Optional[str] = None,
                                 tags: List[str] = None):
        """Store successful implementation in RAG."""
        if not self._rag_integration:
            return
            
        metadata = {
            "agent_id": self.context.agent_id,
            "task_id": task_id,
            "tags": tags or []
        }
        
        if task_id and self._task_integration:
            task = self._task_integration.get_task(task_id)
            if task:
                metadata["task_title"] = task.title
                metadata["task_community"] = task.community_id
                
        await self._rag_integration.store_implementation(
            code,
            description,
            metadata
        )
        
    # Agent Coordination
    
    async def request_from_agent(self, 
                               target_agent: str,
                               request_type: str, 
                               payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to another agent."""
        if not self._event_integration:
            return None
            
        # Create request ID for tracking
        request_id = f"{self.context.agent_id}_{target_agent}_{request_type}"
        
        # Set up response handler
        response_event = f"agent.{self.context.agent_id}.response.{request_id}"
        response = None
        
        async def handle_response(event: Dict[str, Any]):
            nonlocal response
            response = event.get("payload")
            
        # Subscribe to response
        self.context.event_bridge.subscribe(response_event, handle_response)
        
        # Send request
        await self._event_integration.publish_event(
            f"agent.{target_agent}.request",
            {
                "type": request_type,
                "payload": payload,
                "sender_id": self.context.agent_id,
                "response_event": response_event
            }
        )
        
        # Wait for response (with timeout)
        import asyncio
        try:
            await asyncio.wait_for(
                self._wait_for_response(response),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for response from {target_agent}")
            
        # Unsubscribe
        self.context.event_bridge.unsubscribe(response_event, handle_response)
        
        return response
        
    async def _wait_for_response(self, response):
        """Wait for response to be set."""
        import asyncio
        while response is None:
            await asyncio.sleep(0.1)
            

class TaskGraphIntegrationImpl(TaskGraphIntegration):
    """Implementation of task graph integration."""
    
    def __init__(self, task_manager: TaskGraphManager, agent_id: str, event_publisher=None):
        self.task_manager = task_manager
        self.agent_id = agent_id
        self.event_publisher = event_publisher
        self.logger = get_logger(f"{self.__class__.__name__}[{agent_id}]")
        
        # Update task manager context with event publisher if provided
        if event_publisher and hasattr(self.task_manager, 'context'):
            self.task_manager.context.event_publisher = event_publisher
        
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details."""
        task = self.task_manager.graph.tasks.get(task_id)
        return task.to_dict() if task else None
        
    async def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """Retrieve full context for a specific task."""
        task = self.task_manager.graph.tasks.get(task_id)
        if not task:
            return {}
            
        # Get task details and related context
        context = {
            "task": task.to_dict(),
            "parent": None,
            "subtasks": [],
            "dependencies": [],
            "dependents": [],
            "community": None,
            "rag_context": task.rag_context.__dict__ if task.rag_context else {}
        }
        
        # Add parent task
        if task.parent_id and task.parent_id in self.task_manager.graph.tasks:
            parent = self.task_manager.graph.tasks[task.parent_id]
            context["parent"] = parent.to_dict()
            
        # Add subtasks
        for subtask_id in task.subtask_ids:
            if subtask_id in self.task_manager.graph.tasks:
                subtask = self.task_manager.graph.tasks[subtask_id]
                context["subtasks"].append(subtask.to_dict())
                
        # Add dependencies
        for dep_id in task.dependencies:
            if dep_id in self.task_manager.graph.tasks:
                dep = self.task_manager.graph.tasks[dep_id]
                context["dependencies"].append(dep.to_dict())
                
        # Add dependents
        for dep_id in task.dependents:
            if dep_id in self.task_manager.graph.tasks:
                dep = self.task_manager.graph.tasks[dep_id]
                context["dependents"].append(dep.to_dict())
                
        # Add community info
        if task.community_id and task.community_id in self.task_manager.graph.communities:
            community = self.task_manager.graph.communities[task.community_id]
            context["community"] = {
                "id": community.id,
                "name": community.name,
                "theme": community.theme,
                "task_count": len(community.task_ids)
            }
            
        return context
        
    async def update_task_status(self, 
                               task_id: str, 
                               status: TaskStatus,
                               message: Optional[str] = None,
                               metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status."""
        task = self.task_manager.graph.tasks.get(task_id)
        if task:
            task.status = status
            if message:
                task.metadata["status_message"] = message
            if metrics:
                task.metadata["metrics"] = metrics
            self.logger.info(f"Updated task {task_id} to {status.value}")
            return True
        return False
            
    async def create_subtask(self,
                           parent_task_id: str,
                           title: str,
                           description: str,
                           agent_type: str,
                           priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        """Create a subtask."""
        node = await self.task_manager.create_task_from_description(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_task_id,
            agent_type=agent_type
        )
        return node.id
        
    async def add_task_dependency(self, task_id: str, depends_on: str):
        """Add task dependency."""
        task = self.task_manager.graph.tasks.get(task_id)
        dependent_task = self.task_manager.graph.tasks.get(depends_on)
        
        if task and dependent_task:
            # Add dependency to the task
            task.dependencies.add(depends_on)
            # Add this task as a dependent of the other
            dependent_task.dependents.add(task_id)
        
    async def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get task dependencies."""
        task = self.task_manager.graph.tasks.get(task_id)
        return list(task.dependencies) if task else []
        
    async def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get dependent tasks."""
        task = self.task_manager.graph.tasks.get(task_id)
        return list(task.dependents) if task else []
        
    def get_assigned_tasks(self) -> List[EnhancedTaskNode]:
        """Get tasks assigned to this agent."""
        assigned = []
        for task in self.task_manager.graph.tasks.values():
            if task.agent_type == self.agent_id or task.assigned_agent == self.agent_id:
                assigned.append(task)
        return assigned
        

class RAGIntegrationImpl(RAGIntegration):
    """Implementation of RAG integration."""
    
    def __init__(self, rag_client: Any, agent_id: str):
        self.rag_client = rag_client
        self.agent_id = agent_id
        self.logger = get_logger(f"{self.__class__.__name__}[{agent_id}]")
        
    async def search_knowledge(self, 
                             query: str,
                             filter_type: str = None,
                             limit: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        try:
            results = self.rag_client.search(
                query,
                k=limit,
                filters={"type": filter_type} if filter_type else None
            )
            return [
                {
                    "content": r.chunk.content,
                    "metadata": r.chunk.metadata if hasattr(r.chunk, 'metadata') else {},
                    "score": r.score
                }
                for r in results
            ]
        except Exception as e:
            self.logger.error(f"RAG search error: {e}")
            return []
            
    async def store_pattern(self,
                          pattern: str,
                          description: str,
                          example: str,
                          tags: List[str] = None):
        """Store a pattern."""
        self.rag_client.add_document(
            content=f"Pattern: {pattern}\n\n{description}\n\nExample:\n{example}",
            metadata={
                "type": "pattern",
                "pattern_name": pattern,
                "agent_id": self.agent_id,
                "tags": tags or []
            }
        )
        
    async def store_implementation(self,
                                 code: str,
                                 description: str,
                                 metadata: Dict[str, Any] = None):
        """Store implementation."""
        doc_metadata = {
            "type": "implementation",
            "agent_id": self.agent_id,
            "description": description
        }
        if metadata:
            doc_metadata.update(metadata)
            
        # Note: The current RAG service doesn't support adding documents dynamically
        # This would require extending the RAG service with document storage capabilities
        # For now, we'll log this as a future enhancement
        self.logger.debug(f"Would store implementation: {doc_metadata.get('type', 'unknown')} - {description}")
        
    async def find_similar_implementations(self,
                                         description: str,
                                         limit: int = 3) -> List[Dict[str, Any]]:
        """Find similar implementations."""
        return await self.search_knowledge(
            description,
            filter_type="implementation",
            limit=limit
        )
        
    async def get_component_context(self,
                                  component_name: str) -> Dict[str, Any]:
        """Get full context for a code component."""
        try:
            # Search for component-related documentation and implementations
            results = await self.search_knowledge(
                f"component {component_name}",
                filter_type="component",
                limit=10
            )
            
            # Organize results by type
            context = {
                "component_name": component_name,
                "implementations": [],
                "documentation": [],
                "tests": [],
                "usages": []
            }
            
            for result in results:
                metadata = result.get("metadata", {})
                content_type = metadata.get("content_type", "unknown")
                
                if content_type == "implementation":
                    context["implementations"].append(result)
                elif content_type == "documentation":
                    context["documentation"].append(result)
                elif content_type == "test":
                    context["tests"].append(result)
                elif content_type == "usage":
                    context["usages"].append(result)
                    
            return context
        except Exception as e:
            self.logger.error(f"Error getting component context: {e}")
            return {"component_name": component_name, "error": str(e)}
            
    async def store_knowledge(self,
                            doc_type: str,
                            content: str,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store new knowledge in the system."""
        try:
            doc_metadata = {
                "type": doc_type,
                "agent_id": self.agent_id,
                "timestamp": str(datetime.now())
            }
            if metadata:
                doc_metadata.update(metadata)
                
            # Add document to RAG
            doc_id = self.rag_client.add_document(
                content=content,
                metadata=doc_metadata
            )
            
            self.logger.info(f"Stored {doc_type} knowledge: {doc_id}")
            return doc_id
        except Exception as e:
            self.logger.error(f"Error storing knowledge: {e}")
            return ""
        

class EventIntegrationImpl(EventIntegration):
    """Implementation of event integration."""
    
    def __init__(self, event_bridge: EventBridge, agent_id: str, simple_bridge=None):
        self.event_bridge = event_bridge
        self.agent_id = agent_id
        self.simple_bridge = simple_bridge
        
    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event."""
        event_data = {
            "type": event_type,
            "agent_id": self.agent_id,
            **data
        }
        
        if self.simple_bridge:
            await self.simple_bridge.emit(event_data)
        else:
            # Fallback - would need to create typed message
            pass
        
    def subscribe_to_event(self, event_type: str, handler):
        """Subscribe to events."""
        if self.simple_bridge:
            self.simple_bridge.subscribe(event_type, handler)
        else:
            # Fallback - would need to implement typed message subscription
            pass
        
    def unsubscribe_from_event(self, event_type: str, handler):
        """Unsubscribe from events."""
        if self.simple_bridge:
            self.simple_bridge.unsubscribe(event_type, handler)
            
    async def subscribe_to_events(self,
                                event_types: List[str],
                                callback: Any) -> str:
        """Subscribe to specific event types."""
        subscription_id = f"{self.agent_id}_{'-'.join(event_types)}_{id(callback)}"
        
        for event_type in event_types:
            self.subscribe_to_event(event_type, callback)
            
        return subscription_id
        
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        # In a real implementation, we would track subscriptions
        # For now, this is a no-op since unsubscribe_from_event handles it
        pass