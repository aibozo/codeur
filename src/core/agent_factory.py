"""
Factory for creating integrated agents with proper connections.

This provides a central place to create agents with all necessary
integrations configured.
"""

import logging
from typing import Dict, Any, Optional, Type, List
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
from .git_workflow import GitWorkflow, BranchNamingConfig
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
        
        # Create SimpleEventBridge wrapper for string-based events
        from .simple_event_bridge import SimpleEventBridge
        self.simple_event_bridge = SimpleEventBridge(event_bridge)
        
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
        
        # Create git workflow system for enhanced git operations
        self.git_workflow = GitWorkflow(
            repo_path=str(project_path),
            event_bridge=event_bridge,
            naming_config=BranchNamingConfig()
        )
        
        # Create branch manager for handling git operations (legacy support)
        from .branch_manager import BranchManager
        self.branch_manager = BranchManager(
            project_path=project_path,
            event_bridge=event_bridge,
            target_branch="main",  # Default target branch
            gitless_mode=False,  # Can be configured via settings
            simple_event_bridge=self.simple_event_bridge,
            git_workflow=self.git_workflow
        )
        
        # Create self-healing coordinator
        from .self_healing_coordinator import SelfHealingCoordinator
        self.self_healing_coordinator = SelfHealingCoordinator(
            event_bridge=event_bridge,
            rag_client=self.rag_client,
            architect_agent=None  # Will be set after architect is created
        )
        
        # Create retry handler factory
        from .retry_handlers import RetryHandlerFactory
        self.retry_handler_factory = RetryHandlerFactory(
            event_bridge=event_bridge,
            rag_client=self.rag_client
        )
        
        # Enhance RAG client with retry capabilities if available
        if self.rag_client:
            from ..rag_service.retry_enhanced_client import RetryEnhancedRAGClient
            self.rag_client = RetryEnhancedRAGClient(self.rag_client)
        
        # Track created agents
        self.agents: Dict[str, IntegratedAgentBase] = {}
        
        # Session management
        self.session_id: Optional[str] = None
        self.working_branch: Optional[str] = None
        
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
        context = AgentContext(
            project_path=self.project_path,
            event_bridge=self.event_bridge,
            task_manager=self.task_manager,
            rag_client=self.rag_client,
            agent_id=agent_id
        )
        # Add git workflow to context
        context.git_workflow = self.git_workflow
        return context
        
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
        
        # Link architect to self-healing coordinator
        self.self_healing_coordinator.architect_agent = architect
        
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
        
    async def create_test_agent(self, **kwargs) -> 'IntegratedTestAgent':
        """Create an integrated Test agent."""
        # Import here to avoid circular imports
        from ..test_agent.integrated_test_agent import IntegratedTestAgent
        
        context = self.create_agent_context("test_agent")
        agent = IntegratedTestAgent(context)
        
        # Register with agent registry
        await self.agent_registry.register_agent(
            agent_type="test_agent",
            model="local",
            capabilities=["testing", "test_generation", "test_execution", "test_analysis"]
        )
        
        self.agents["test_agent"] = agent
        logger.info("Created integrated Test agent")
        
        return agent
        
    async def create_all_agents(self) -> Dict[str, IntegratedAgentBase]:
        """Create all integrated agents."""
        logger.info("Creating all integrated agents...")
        
        # Create agents in dependency order
        await self.create_architect()
        await self.create_request_planner()
        await self.create_code_planner()
        await self.create_coding_agent()
        await self.create_test_agent()
        await self.create_analyzer()
        
        logger.info(f"Created {len(self.agents)} integrated agents")
        return self.agents
        
    def get_agent(self, agent_id: str) -> Optional[IntegratedAgentBase]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
        
    def set_target_branch(self, branch_name: str):
        """
        Set the target branch for merging.
        
        Args:
            branch_name: Name of the target branch (e.g., "main", "develop")
        """
        self.branch_manager.set_target_branch(branch_name)
        
    def set_gitless_mode(self, enabled: bool):
        """
        Enable or disable gitless mode.
        
        Args:
            enabled: If True, skip all git operations
        """
        self.branch_manager.set_gitless_mode(enabled)
        
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
        
    async def start_session(self, user_id: str = "default") -> str:
        """
        Start a new working session with git workflow.
        
        Args:
            user_id: Identifier for the user/session
            
        Returns:
            The working branch name
        """
        import uuid
        
        # Generate session ID
        self.session_id = str(uuid.uuid4())[:8]
        
        # Start git workflow session
        self.working_branch = await self.git_workflow.start_session(
            session_id=self.session_id,
            user_id=user_id
        )
        
        logger.info(f"Started session {self.session_id} on branch {self.working_branch}")
        return self.working_branch
        
    async def create_task_branch(self, task_id: str, description: str, agent_id: str = "system") -> str:
        """
        Create a task branch for specific work.
        
        Args:
            task_id: Unique task identifier
            description: Brief description of the task
            agent_id: Agent that will work on this task
            
        Returns:
            The task branch name
        """
        return await self.git_workflow.create_task_branch_async(task_id, description, agent_id)
        
    async def commit_work(
        self, 
        task_id: str, 
        agent_id: str, 
        message: str, 
        commit_type: Optional[str] = None
    ) -> str:
        """
        Create an atomic commit for completed work.
        
        Args:
            task_id: Task identifier
            agent_id: Agent that did the work
            message: Commit message
            commit_type: Type of commit (feature, fix, etc.)
            
        Returns:
            Commit SHA
        """
        from .git_workflow import CommitType
        
        # Convert string to enum if provided
        if commit_type:
            try:
                ct = CommitType(commit_type.lower())
            except ValueError:
                ct = CommitType.FEATURE
        else:
            ct = CommitType.FEATURE
            
        return await self.git_workflow.commit_atomic(
            task_id=task_id,
            agent_id=agent_id,
            message=message,
            commit_type=ct
        )
        
    async def create_checkpoint(self, description: str) -> Dict[str, Any]:
        """
        Create a checkpoint of the current state.
        
        Args:
            description: Description of the checkpoint
            
        Returns:
            Checkpoint information
        """
        checkpoint = await self.git_workflow.create_checkpoint_async(description)
        return {
            "id": checkpoint.id,
            "branch_name": checkpoint.branch_name,
            "description": checkpoint.description,
            "timestamp": checkpoint.timestamp.isoformat()
        }
        
    def get_git_history(self, max_commits: int = 20) -> str:
        """
        Get visual git history.
        
        Args:
            max_commits: Maximum number of commits to show
            
        Returns:
            Visual git history as text
        """
        return self.git_workflow.get_visual_history(max_commits)
        
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint information
        """
        return self.git_workflow.list_checkpoints()
        
    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore the project to a specific checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint to restore
            
        Returns:
            True if successful
        """
        success = self.git_workflow.restore_checkpoint(checkpoint_id)
        if success:
            logger.info(f"Restored to checkpoint {checkpoint_id}")
        else:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}")
        return success
        
    async def revert_task(self, task_id: str, cascade: bool = True) -> bool:
        """
        Revert changes from a specific task.
        
        Args:
            task_id: Task to revert
            cascade: Whether to revert dependent tasks
            
        Returns:
            True if successful
        """
        success = self.git_workflow.revert_task(task_id, cascade)
        if success:
            logger.info(f"Reverted task {task_id}")
            # Create checkpoint after reversion
            await self.create_checkpoint(f"after-revert-{task_id}")
        else:
            logger.error(f"Failed to revert task {task_id}")
        return success
        
    async def revert_task_files(self, task_id: str, file_paths: List[str]) -> bool:
        """
        Selectively revert specific files from a task.
        
        Args:
            task_id: Task whose changes to revert
            file_paths: List of file paths to revert
            
        Returns:
            True if successful
        """
        success = self.git_workflow.revert_task_files(task_id, file_paths)
        if success:
            logger.info(f"Selectively reverted {len(file_paths)} files from task {task_id}")
        else:
            logger.error(f"Failed to selectively revert files from task {task_id}")
        return success
        
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task information including commit, files, dependent tasks
        """
        return self.git_workflow.get_task_info(task_id)
        
    def get_git_visualization_data(self, max_commits: int = 50) -> Dict[str, Any]:
        """
        Get git visualization data for frontend display.
        
        Args:
            max_commits: Maximum number of commits to include
            
        Returns:
            Dictionary with nodes, edges, and metadata for visualization
        """
        from ..ui.git_visualizer import GitVisualizer
        
        visualizer = GitVisualizer(str(self.project_path))
        return visualizer.get_graph_data_json(max_commits)
        
    def get_git_activity_history(self, max_items: int = 20) -> List[Dict[str, Any]]:
        """
        Get compact git activity history for frontend activity feed.
        
        Args:
            max_items: Maximum number of items to return
            
        Returns:
            List of recent git activities
        """
        from ..ui.git_visualizer import GitVisualizer
        
        visualizer = GitVisualizer(str(self.project_path))
        return visualizer.get_compact_history(max_items)
        

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
    
    # Automatically start a working session
    try:
        working_branch = await factory.start_session(user_id="system")
        logger.info(f"Automatically started working session on branch: {working_branch}")
    except Exception as e:
        logger.warning(f"Failed to start automatic working session: {e}")
        working_branch = None
    
    return {
        "factory": factory,
        "agents": agents,
        "event_bridge": event_bridge,
        "task_manager": factory.task_manager,
        "rag_client": factory.rag_client,
        "git_workflow": factory.git_workflow,
        "working_branch": working_branch,
        "settings": settings
    }