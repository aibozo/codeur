"""
Factory for creating integrated agents with proper connections.

This provides a central place to create agents with all necessary
integrations configured.
"""

import logging
from typing import Dict, Any, Optional, Type
from pathlib import Path

from .integrated_agent_base import AgentContext, IntegratedAgentBase
from .event_bridge import EventBridge
from .agent_registry import AgentRegistry
from .settings import Settings
from ..architect.task_graph_manager import TaskGraphManager, TaskGraphContext
from ..architect.architect import Architect
from ..request_planner.integrated_request_planner import IntegratedRequestPlanner
from ..coding_agent.agent import CodingAgent
from ..code_planner.code_planner import CodePlanner
from ..analyzer.analyzer import Analyzer
from .logging import get_logger

# Optional RAG import
try:
    from ..rag_service import RAGService, RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGService = None
    RAGClient = None
    RAG_AVAILABLE = False

logger = get_logger(__name__)


class IntegratedAgentFactory:
    """
    Factory for creating agents with full integration support.
    """
    
    def __init__(self,
                 project_path: Path,
                 event_bridge: EventBridge,
                 settings: Settings,
                 rag_service: Optional[Any] = None):
        """
        Initialize agent factory.
        
        Args:
            project_path: Path to the project
            event_bridge: Event bridge for agent communication
            settings: System settings
            rag_service: Optional RAG service
        """
        self.project_path = project_path
        self.event_bridge = event_bridge
        self.settings = settings
        self.rag_service = rag_service
        self.rag_client = None
        
        # Create RAG client if service available
        if rag_service and RAG_AVAILABLE:
            self.rag_client = RAGClient(service=rag_service)
            # Set project context if adaptive
            if hasattr(self.rag_client, 'set_project_context'):
                self.rag_client.set_project_context(f"project_{project_path.name}")
        elif RAG_AVAILABLE and not rag_service:
            # Create default RAG service (will be adaptive if enabled)
            rag_dir = project_path / ".rag"
            rag_dir.mkdir(exist_ok=True)
            self.rag_service = RAGService(
                persist_directory=str(rag_dir),
                repo_path=str(project_path)
            )
            self.rag_client = RAGClient(service=self.rag_service)
            # Set project context if adaptive
            if hasattr(self.rag_client, 'set_project_context'):
                self.rag_client.set_project_context(f"project_{project_path.name}")
            
        # Create shared task graph manager
        self.task_context = TaskGraphContext(
            project_id=f"project_{project_path.name}",
            project_path=project_path,
            rag_client=self.rag_client,
            event_publisher=self._create_event_publisher()
        )
        self.task_manager = TaskGraphManager(self.task_context)
        
        # Agent registry
        self.agent_registry = AgentRegistry(event_bridge)
        
        # Track created agents
        self.agents: Dict[str, IntegratedAgentBase] = {}
        
    def _create_event_publisher(self):
        """Create an event publisher that works with the test infrastructure."""
        def publish_event(event_type: str, data: Dict[str, Any]):
            # For compatibility with tests that expect string-based events
            # We'll publish directly to any handlers subscribed to "*"
            if hasattr(self.event_bridge.message_bus, '_subscribers'):
                wildcard_handlers = self.event_bridge.message_bus._subscribers.get("*", [])
                logger.debug(f"Publishing event {event_type} to {len(wildcard_handlers)} wildcard handlers")
                for handler in wildcard_handlers:
                    try:
                        handler(event_type, data)
                    except Exception as e:
                        logger.warning(f"Error in wildcard handler: {e}")
            else:
                logger.warning(f"No _subscribers attribute on message bus")
        
        return publish_event
        
    def create_agent_context(self, agent_id: str) -> AgentContext:
        """Create context for an agent."""
        return AgentContext(
            project_path=self.project_path,
            event_bridge=self.event_bridge,
            task_manager=self.task_manager,
            rag_client=self.rag_client,
            agent_id=agent_id
        )
        
    async def create_architect(self, **kwargs) -> Architect:
        """
        Create an integrated Architect agent.
        
        The architect already has enhanced task graph support built in.
        """
        architect = Architect(
            project_path=str(self.project_path),
            rag_service=self.rag_service,
            use_enhanced_task_graph=True,
            **kwargs
        )
        
        # Register with agent registry
        await self.agent_registry.register_agent(
            agent_type="architect",
            model="local",
            capabilities=["planning", "architecture", "task_creation"]
        )
        
        self.agents["architect"] = architect
        logger.info("Created integrated Architect agent")
        
        return architect
        
    async def create_request_planner(self, **kwargs) -> IntegratedRequestPlanner:
        """Create an integrated Request Planner agent."""
        context = self.create_agent_context("request_planner")
        planner = IntegratedRequestPlanner(context)
        
        # Register with agent registry
        await self.agent_registry.register_agent(
            agent_type="request_planner",
            model="local",
            capabilities=["planning", "task_decomposition", "coordination"]
        )
        
        self.agents["request_planner"] = planner
        logger.info("Created integrated Request Planner agent")
        
        return planner
        
    async def create_coding_agent(self, **kwargs) -> 'IntegratedCodingAgent':
        """Create an integrated Coding agent."""
        # Import here to avoid circular imports
        from ..coding_agent.integrated_coding_agent import IntegratedCodingAgent
        
        context = self.create_agent_context("coding_agent")
        agent = IntegratedCodingAgent(context)
        
        # Register with agent registry
        await self.agent_registry.register_agent(
            agent_type="coding_agent",
            model="local",
            capabilities=["coding", "implementation", "refactoring"]
        )
        
        self.agents["coding_agent"] = agent
        logger.info("Created integrated Coding agent")
        
        return agent
        
    async def create_code_planner(self, **kwargs) -> 'IntegratedCodePlanner':
        """Create an integrated Code Planner agent."""
        # Import here to avoid circular imports
        from ..code_planner.integrated_code_planner import IntegratedCodePlanner
        
        context = self.create_agent_context("code_planner")
        agent = IntegratedCodePlanner(context)
        
        # Register with agent registry
        await self.agent_registry.register_agent(
            agent_type="code_planner",
            model="local",
            capabilities=["code_analysis", "dependency_analysis", "planning"]
        )
        
        self.agents["code_planner"] = agent
        logger.info("Created integrated Code Planner agent")
        
        return agent
        
    async def create_analyzer(self, **kwargs) -> 'IntegratedAnalyzer':
        """Create an integrated Analyzer agent."""
        # Import here to avoid circular imports
        from ..analyzer.integrated_analyzer import IntegratedAnalyzer
        
        context = self.create_agent_context("analyzer")
        agent = IntegratedAnalyzer(context)
        
        # Register with agent registry
        await self.agent_registry.register_agent(
            agent_type="analyzer",
            model="local",
            capabilities=["analysis", "architecture_review", "quality_check"]
        )
        
        self.agents["analyzer"] = agent
        logger.info("Created integrated Analyzer agent")
        
        return agent
        
    async def create_all_agents(self) -> Dict[str, IntegratedAgentBase]:
        """Create all integrated agents."""
        logger.info("Creating all integrated agents...")
        
        # Create agents in dependency order
        await self.create_architect()
        await self.create_request_planner()
        await self.create_code_planner()
        await self.create_coding_agent()
        await self.create_analyzer()
        
        logger.info(f"Created {len(self.agents)} integrated agents")
        return self.agents
        
    def get_agent(self, agent_id: str) -> Optional[IntegratedAgentBase]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
        
    async def shutdown(self):
        """Shutdown all agents and clean up."""
        logger.info("Shutting down integrated agents...")
        
        # Shutdown each agent
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'shutdown'):
                await agent.shutdown()
                
        # Clear registry
        self.agents.clear()
        
        logger.info("Agent shutdown complete")
        

# Convenience function
async def create_integrated_agent_system(
    project_path: str,
    settings: Optional[Settings] = None
) -> Dict[str, Any]:
    """
    Create a complete integrated agent system.
    
    This is a convenience function that sets up everything needed
    for a fully integrated agent system.
    
    Args:
        project_path: Path to the project
        settings: Optional settings (uses defaults if not provided)
        
    Returns:
        Dictionary with all components:
        - factory: The agent factory
        - agents: Dictionary of all created agents
        - event_bridge: Event bridge for communication
        - task_manager: Task graph manager
        - rag_client: RAG client (if available)
    """
    from ..core.message_bus import MessageBus
    from ..core.realtime import RealtimeService
    
    # Create settings if not provided
    if not settings:
        settings = Settings()
        
    # Create infrastructure
    message_bus = MessageBus()
    realtime_service = RealtimeService(settings)
    event_bridge = EventBridge(message_bus, realtime_service)
    
    # Create factory
    factory = IntegratedAgentFactory(
        project_path=Path(project_path),
        event_bridge=event_bridge,
        settings=settings
    )
    
    # Create all agents
    agents = await factory.create_all_agents()
    
    return {
        "factory": factory,
        "agents": agents,
        "event_bridge": event_bridge,
        "task_manager": factory.task_manager,
        "rag_client": factory.rag_client,
        "settings": settings
    }