"""
Agent Integration Interfaces for Task Graph and RAG Systems.

This module defines the standard interfaces that all agents should implement
to integrate with the task graph and RAG systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.architect.models import TaskStatus, TaskPriority
from src.rag_service import RAGClient


class IntegrationLevel(Enum):
    """Level of integration an agent needs."""
    NONE = "none"
    TASK_ONLY = "task_only"
    RAG_ONLY = "rag_only"
    FULL = "full"


class AgentCapability(Enum):
    """Capabilities that agents can have."""
    # Core capabilities
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    
    # Task-related
    TASK_DECOMPOSITION = "task_decomposition"
    TASK_SCHEDULING = "task_scheduling"
    
    # Coordination
    COORDINATION = "coordination"
    ARCHITECTURE = "architecture"
    CODE_ANALYSIS = "code_analysis"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    ARCHITECTURE_REVIEW = "architecture_review"
    QUALITY_CHECK = "quality_check"
    
    # System capabilities (old ones kept for compatibility)
    TASK_READ = "task_read"
    TASK_WRITE = "task_write"
    RAG_READ = "rag_read"
    RAG_WRITE = "rag_write"
    EVENT_PUBLISH = "event_publish"
    EVENT_SUBSCRIBE = "event_subscribe"


@dataclass
class AgentContext:
    """Context provided to agents for integration."""
    agent_id: str
    agent_type: str
    project_id: str
    task_graph_manager: Optional[Any] = None
    rag_client: Optional[RAGClient] = None
    event_bus: Optional[Any] = None
    capabilities: List[AgentCapability] = None


class TaskGraphIntegration(ABC):
    """Interface for agents that need task graph access."""
    
    @abstractmethod
    async def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """Retrieve full context for a specific task."""
        pass
    
    @abstractmethod
    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the status of a task."""
        pass
    
    @abstractmethod
    async def create_subtask(
        self,
        parent_task_id: str,
        title: str,
        description: str,
        agent_type: str,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """Create a subtask under a parent task."""
        pass
    
    @abstractmethod
    async def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get all dependencies for a task."""
        pass
    
    @abstractmethod
    async def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get all tasks that depend on this task."""
        pass


class RAGIntegration(ABC):
    """Interface for agents that need RAG system access."""
    
    @abstractmethod
    async def search_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base."""
        pass
    
    @abstractmethod
    async def store_knowledge(
        self,
        doc_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store new knowledge in the system."""
        pass
    
    @abstractmethod
    async def find_similar_implementations(
        self,
        description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past implementations."""
        pass
    
    @abstractmethod
    async def get_component_context(
        self,
        component_name: str
    ) -> Dict[str, Any]:
        """Get full context for a code component."""
        pass


class EventIntegration(ABC):
    """Interface for agents that need event system access."""
    
    @abstractmethod
    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Publish an event to the system."""
        pass
    
    @abstractmethod
    async def subscribe_to_events(
        self,
        event_types: List[str],
        callback: Any
    ) -> str:
        """Subscribe to specific event types."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        pass


class IntegratedAgent(ABC):
    """Base class for agents with full integration support."""
    
    def __init__(self, context: AgentContext):
        self.context = context
        self._task_integration = None
        self._rag_integration = None
        self._event_integration = None
        
        # Initialize integrations based on capabilities
        if context.capabilities:
            self._setup_integrations()
    
    def _setup_integrations(self):
        """Setup integrations based on agent capabilities."""
        if any(cap in [AgentCapability.TASK_READ, AgentCapability.TASK_WRITE] 
               for cap in self.context.capabilities):
            self._task_integration = self._create_task_integration()
        
        if any(cap in [AgentCapability.RAG_READ, AgentCapability.RAG_WRITE]
               for cap in self.context.capabilities):
            self._rag_integration = self._create_rag_integration()
        
        if any(cap in [AgentCapability.EVENT_PUBLISH, AgentCapability.EVENT_SUBSCRIBE]
               for cap in self.context.capabilities):
            self._event_integration = self._create_event_integration()
    
    @abstractmethod
    def _create_task_integration(self) -> TaskGraphIntegration:
        """Create task graph integration instance."""
        pass
    
    @abstractmethod
    def _create_rag_integration(self) -> RAGIntegration:
        """Create RAG integration instance."""
        pass
    
    @abstractmethod
    def _create_event_integration(self) -> EventIntegration:
        """Create event integration instance."""
        pass
    
    @property
    def task_graph(self) -> Optional[TaskGraphIntegration]:
        """Access task graph integration."""
        return self._task_integration
    
    @property
    def rag(self) -> Optional[RAGIntegration]:
        """Access RAG integration."""
        return self._rag_integration
    
    @property
    def events(self) -> Optional[EventIntegration]:
        """Access event integration."""
        return self._event_integration


# Standard event types for agent communication
class AgentEventType:
    """Standard event types used by agents."""
    TASK_CREATED = "agent.task.created"
    TASK_STARTED = "agent.task.started"
    TASK_COMPLETED = "agent.task.completed"
    TASK_FAILED = "agent.task.failed"
    
    PLAN_CREATED = "agent.plan.created"
    PLAN_EXECUTED = "agent.plan.executed"
    
    CODE_ANALYZED = "agent.code.analyzed"
    CODE_CHANGED = "agent.code.changed"
    CODE_COMMITTED = "agent.code.committed"
    
    ARCHITECTURE_ANALYZED = "agent.architecture.analyzed"
    ARCHITECTURE_CHANGED = "agent.architecture.changed"
    
    TEST_STARTED = "agent.test.started"
    TEST_COMPLETED = "agent.test.completed"
    TEST_FAILED = "agent.test.failed"


# Helper functions for creating standard integrations
def create_agent_context(
    agent_id: str,
    agent_type: str,
    project_id: str,
    capabilities: List[AgentCapability],
    task_graph_manager: Optional[Any] = None,
    rag_client: Optional[RAGClient] = None,
    event_bus: Optional[Any] = None
) -> AgentContext:
    """Create a standard agent context."""
    return AgentContext(
        agent_id=agent_id,
        agent_type=agent_type,
        project_id=project_id,
        task_graph_manager=task_graph_manager,
        rag_client=rag_client,
        event_bus=event_bus,
        capabilities=capabilities
    )