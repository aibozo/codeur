#!/usr/bin/env python3
"""
Comprehensive Task Graph Integration Demonstration

This demo shows how the enhanced task graph integrates with the existing agent
system, including:
- EventBridge integration for task events
- RAG context attachment
- Task assignment via agent capabilities
- Inter-graph communication
- Real-world usage patterns
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Core imports
from src.core.message_bus import MessageBus, Message
from src.core.event_bridge import (
    EventBridge, emit_agent_status, emit_task_progress,
    emit_log, emit_job_update, AgentMessageFlow
)
from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core.agent_graph import AgentGraph
from src.core.realtime import RealtimeService
from src.core.task_scheduler import TaskScheduler

# Architect imports
from src.architect.enhanced_task_graph import (
    EnhancedTaskGraph, EnhancedTaskNode, TaskCommunity,
    TaskPriority, TaskStatus, TaskGranularity, DisplayMode
)
from src.architect.task_graph_manager import TaskGraphManager, TaskGraphContext

# RAG imports (optional)
try:
    from src.rag_service.client import RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGClient = None
    RAG_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Custom message types for task events
from dataclasses import dataclass

@dataclass
class TaskCreatedMessage(Message):
    """Emitted when a new task is created."""
    task_id: str
    task_title: str
    agent_type: str
    community_id: Optional[str] = None


@dataclass
class TaskStatusMessage(Message):
    """Emitted when task status changes."""
    task_id: str
    old_status: str
    new_status: str
    agent_type: Optional[str] = None


@dataclass
class TaskRAGAttachedMessage(Message):
    """Emitted when RAG context is attached to a task."""
    task_id: str
    chunk_count: int
    file_patterns: List[str]


class TaskGraphDemo:
    """Demonstration of task graph integration."""
    
    def __init__(self):
        """Initialize demo components."""
        # Core infrastructure
        self.message_bus = MessageBus()
        self.agent_registry = AgentRegistry(message_bus=self.message_bus)
        self.agent_graph = AgentGraph()
        
        # Task management
        self.scheduler = TaskScheduler(self.agent_registry)
        
        # RAG service (if available)
        self.rag_client = RAGClient() if RAG_AVAILABLE else None
        
        # Task graph manager
        self.context = TaskGraphContext(
            project_id="demo_project",
            project_path=Path("."),
            rag_client=self.rag_client,
            agent_registry=self.agent_registry,
            scheduler=self.scheduler
        )
        self.task_manager = TaskGraphManager(self.context)
        
        # Event bridge (mock realtime service for demo)
        self.event_bridge = EventBridge(
            self.message_bus,
            realtime_service=None,  # Would be real WebSocket service
            agent_registry=self.agent_registry
        )
        
        # Set up event subscriptions
        self._setup_subscriptions()
        
    def _setup_subscriptions(self):
        """Set up message bus subscriptions for demo."""
        # Subscribe to task events
        self.message_bus.subscribe(TaskCreatedMessage, self._handle_task_created)
        self.message_bus.subscribe(TaskStatusMessage, self._handle_task_status)
        self.message_bus.subscribe(TaskRAGAttachedMessage, self._handle_rag_attached)
        
        # Subscribe to agent flow events
        self.message_bus.subscribe(AgentMessageFlow, self._handle_agent_flow)
        
    def _handle_task_created(self, msg: TaskCreatedMessage):
        """Handle task creation events."""
        logger.info(f"Task created: {msg.task_title} (ID: {msg.task_id})")
        logger.info(f"  Assigned to: {msg.agent_type}")
        if msg.community_id:
            logger.info(f"  Community: {msg.community_id}")
            
    def _handle_task_status(self, msg: TaskStatusMessage):
        """Handle task status changes."""
        logger.info(f"Task {msg.task_id} status: {msg.old_status} -> {msg.new_status}")
        
    def _handle_rag_attached(self, msg: TaskRAGAttachedMessage):
        """Handle RAG context attachment."""
        logger.info(f"RAG context attached to task {msg.task_id}:")
        logger.info(f"  Chunks: {msg.chunk_count}")
        logger.info(f"  Files: {msg.file_patterns}")
        
    def _handle_agent_flow(self, msg: AgentMessageFlow):
        """Handle agent message flows."""
        logger.info(f"Agent flow: {msg.from_agent} -> {msg.to_agent} ({msg.message_type})")
        
    async def demo_1_basic_task_creation(self):
        """Demonstrate basic task creation with event emission."""
        logger.info("\n=== Demo 1: Basic Task Creation ===")
        
        # Create a simple task
        task = await self.task_manager.create_task_from_description(
            title="Implement user authentication",
            description="Add JWT-based authentication to the API endpoints",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH
        )
        
        # Emit task created event
        await self.message_bus.publish(TaskCreatedMessage(
            timestamp=datetime.utcnow(),
            source="task_manager",
            data={},
            task_id=task.id,
            task_title=task.title,
            agent_type=task.agent_type,
            community_id=task.community_id
        ))
        
        # Simulate task progress
        await asyncio.sleep(0.5)
        emit_task_progress(
            self.message_bus,
            task_id=task.id,
            progress=0.3,
            status="in_progress",
            details="Setting up authentication middleware"
        )
        
        return task
        
    async def demo_2_hierarchical_tasks(self):
        """Demonstrate hierarchical task creation (Epic -> Tasks -> Subtasks)."""
        logger.info("\n=== Demo 2: Hierarchical Task Structure ===")
        
        # Create an epic with subtasks
        epic = await self.task_manager.create_task_hierarchy(
            epic_title="Build E-commerce Platform",
            epic_description="Complete e-commerce platform with product catalog, cart, and checkout",
            subtasks=[
                {
                    "title": "Design database schema",
                    "description": "Create tables for products, users, orders",
                    "agent_type": "architect",
                    "priority": "HIGH"
                },
                {
                    "title": "Implement product catalog API",
                    "description": "CRUD operations for products with search",
                    "agent_type": "coding_agent",
                    "priority": "HIGH",
                    "dependencies": []  # Depends on schema design
                },
                {
                    "title": "Build shopping cart service",
                    "description": "Cart management with session handling",
                    "agent_type": "coding_agent",
                    "priority": "MEDIUM"
                },
                {
                    "title": "Create checkout flow",
                    "description": "Payment processing and order creation",
                    "agent_type": "coding_agent",
                    "priority": "HIGH",
                    "dependencies": []  # Will be set to depend on cart
                }
            ]
        )
        
        # Set dependencies between subtasks
        subtasks = list(epic.subtask_ids)
        if len(subtasks) >= 4:
            # Make API depend on schema
            self.task_manager.graph.tasks[subtasks[1]].dependencies.add(subtasks[0])
            # Make checkout depend on cart
            self.task_manager.graph.tasks[subtasks[3]].dependencies.add(subtasks[2])
        
        # Emit events for the hierarchy
        await self.message_bus.publish(TaskCreatedMessage(
            timestamp=datetime.utcnow(),
            source="architect",
            data={},
            task_id=epic.id,
            task_title=epic.title,
            agent_type=epic.agent_type
        ))
        
        return epic
        
    async def demo_3_community_detection(self):
        """Demonstrate automatic community detection and RAG attachment."""
        logger.info("\n=== Demo 3: Community Detection & RAG Context ===")
        
        # Create tasks that will form communities
        auth_tasks = []
        for title, desc in [
            ("Setup JWT tokens", "Implement JWT generation and validation"),
            ("Add login endpoint", "Create /auth/login API endpoint"),
            ("Implement user registration", "Create user signup flow"),
            ("Add password reset", "Email-based password reset feature")
        ]:
            task = await self.task_manager.create_task_from_description(
                title=title,
                description=desc,
                agent_type="coding_agent"
            )
            auth_tasks.append(task)
            
        # Detect communities
        communities = self.task_manager.detect_and_create_communities(method="theme")
        
        # Attach RAG context to authentication community
        if communities and self.rag_client:
            auth_community = next((c for c in communities if "auth" in c.theme), None)
            if auth_community:
                await self.task_manager.attach_rag_context_to_community(
                    auth_community.id,
                    queries=["JWT authentication", "user login", "password hashing"]
                )
                
                # Emit RAG attachment events
                for task_id in auth_community.task_ids:
                    task = self.task_manager.graph.tasks.get(task_id)
                    if task:
                        await self.message_bus.publish(TaskRAGAttachedMessage(
                            timestamp=datetime.utcnow(),
                            source="rag_service",
                            data={},
                            task_id=task_id,
                            chunk_count=len(task.rag_context.chunk_ids),
                            file_patterns=task.rag_context.file_patterns
                        ))
                        
        return communities
        
    async def demo_4_architect_to_agents_flow(self):
        """Demonstrate architect creating tasks that flow to other agents."""
        logger.info("\n=== Demo 4: Architect to Agents Task Flow ===")
        
        # Register agents
        await self.agent_registry.register_agent("architect", "gpt-4", 
                                               capabilities=["design", "planning"])
        await self.agent_registry.register_agent("request_planner", "gpt-4",
                                               capabilities=["orchestration"])
        await self.agent_registry.register_agent("code_planner", "gpt-4",
                                               capabilities=["implementation_planning"])
        await self.agent_registry.register_agent("coding_agent", "gpt-4",
                                               capabilities=["coding", "testing"])
        
        # Start scheduler
        await self.scheduler.start()
        
        # Architect creates high-level task
        architect_task = await self.task_manager.create_task_from_description(
            title="Design microservices architecture",
            description="Design a scalable microservices architecture for the platform",
            agent_type="architect",
            priority=TaskPriority.CRITICAL
        )
        
        # Simulate architect completing design and creating implementation tasks
        await asyncio.sleep(1)
        
        # Architect creates implementation tasks for other agents
        impl_tasks = []
        for service_name, agent in [
            ("API Gateway Service", "coding_agent"),
            ("User Service", "coding_agent"),
            ("Product Service", "coding_agent"),
            ("Order Service", "coding_agent")
        ]:
            task = await self.task_manager.create_task_from_description(
                title=f"Implement {service_name}",
                description=f"Build {service_name} following the microservices design",
                agent_type=agent,
                parent_id=architect_task.id,
                priority=TaskPriority.HIGH
            )
            impl_tasks.append(task)
            
            # Emit flow from architect to coding agent
            await self.message_bus.publish(AgentMessageFlow(
                timestamp=datetime.utcnow(),
                source="flow_tracker",
                data={},
                from_agent="architect",
                to_agent=agent,
                message_type="task_assignment",
                payload_size=len(task.description),
                success=True
            ))
        
        # Schedule the implementation tasks
        await self.task_manager.schedule_ready_tasks()
        
        # Wait a bit to see scheduling
        await asyncio.sleep(2)
        
        # Get scheduler status
        status = self.scheduler.get_scheduler_status()
        logger.info(f"\nScheduler Status:")
        logger.info(f"  Active tasks: {status['active_tasks']}")
        logger.info(f"  Queued tasks: {status['queued_tasks']}")
        
        return impl_tasks
        
    async def demo_5_display_modes(self):
        """Demonstrate different display modes for the task graph."""
        logger.info("\n=== Demo 5: Task Graph Display Modes ===")
        
        # Switch to sparse mode
        self.task_manager.graph.display_mode = DisplayMode.SPARSE
        sparse_tasks = self.task_manager.graph.get_display_tasks()
        logger.info(f"\nSparse mode - showing {len(sparse_tasks)} tasks")
        
        # Switch to focused mode
        if self.task_manager.graph.tasks:
            first_task_id = list(self.task_manager.graph.tasks.keys())[0]
            self.task_manager.graph.set_focused_task(first_task_id)
            self.task_manager.graph.display_mode = DisplayMode.FOCUSED
            focused_tasks = self.task_manager.graph.get_display_tasks()
            logger.info(f"Focused mode - showing {len(focused_tasks)} tasks around {first_task_id}")
        
        # Switch to dense mode
        self.task_manager.graph.display_mode = DisplayMode.DENSE
        dense_tasks = self.task_manager.graph.get_display_tasks()
        logger.info(f"Dense mode - showing {len(dense_tasks)} tasks")
        
        # Test task expansion
        for task_id, task in list(self.task_manager.graph.tasks.items())[:2]:
            if task.subtask_ids:
                expanded = self.task_manager.graph.toggle_task_expansion(task_id)
                logger.info(f"Task {task_id} expanded: {expanded}")
                
    async def demo_6_context_abstraction(self):
        """Demonstrate context abstraction for architect."""
        logger.info("\n=== Demo 6: Context Abstraction for Architect ===")
        
        # Get abstracted state (minimal info)
        abstracted = self.task_manager.get_abstracted_state()
        logger.info("\nAbstracted State:")
        logger.info(f"  Total tasks: {abstracted['total_tasks']}")
        logger.info(f"  Completed: {abstracted['completed_tasks']}")
        logger.info(f"  Communities: {len(abstracted['communities'])}")
        logger.info(f"  Top-level tasks: {len(abstracted['top_level_tasks'])}")
        
        # Get expanded context for specific task
        if self.task_manager.graph.tasks:
            task_id = list(self.task_manager.graph.tasks.keys())[0]
            expanded = self.task_manager.expand_task_context(task_id)
            logger.info(f"\nExpanded context for task {task_id}:")
            logger.info(f"  Task: {expanded['task']['title']}")
            if expanded.get('community'):
                logger.info(f"  Community: {expanded['community']['name']}")
            logger.info(f"  RAG chunks: {len(expanded['rag_context']['chunks'])}")
            
    async def demo_7_inter_graph_compatibility(self):
        """Demonstrate compatibility between task_graph and agent_graph."""
        logger.info("\n=== Demo 7: Inter-Graph Compatibility ===")
        
        # Get agent graph data
        agent_data = self.agent_graph.get_graph_data()
        logger.info(f"\nAgent Graph:")
        logger.info(f"  Nodes: {len(agent_data['nodes'])}")
        logger.info(f"  Edges: {len(agent_data['edges'])}")
        
        # Create task-to-agent mapping based on graph
        task_agent_map = {}
        for task_id, task in self.task_manager.graph.tasks.items():
            # Find agent in agent graph
            agent_node = next(
                (n for n in agent_data['nodes'] if n['id'] == task.agent_type),
                None
            )
            if agent_node:
                task_agent_map[task_id] = {
                    'task': task.title,
                    'agent': agent_node['label'],
                    'agent_desc': agent_node['description']
                }
                
        logger.info(f"\nTask-Agent Mappings: {len(task_agent_map)}")
        for mapping in list(task_agent_map.values())[:3]:
            logger.info(f"  '{mapping['task']}' -> {mapping['agent']} ({mapping['agent_desc']})")
            
        # Simulate message flows between agents based on task dependencies
        for task_id, task in self.task_manager.graph.tasks.items():
            for dep_id in task.dependencies:
                if dep_id in self.task_manager.graph.tasks:
                    dep_task = self.task_manager.graph.tasks[dep_id]
                    
                    # Emit flow from dependent task's agent to this task's agent
                    await self.message_bus.publish(AgentMessageFlow(
                        timestamp=datetime.utcnow(),
                        source="task_dependency",
                        data={},
                        from_agent=dep_task.agent_type,
                        to_agent=task.agent_type,
                        message_type="dependency_notification",
                        payload_size=100,
                        success=True
                    ))
                    
    async def demo_8_persistence(self):
        """Demonstrate task graph persistence."""
        logger.info("\n=== Demo 8: Task Graph Persistence ===")
        
        # Save current graph
        save_path = self.task_manager.save_graph("demo_graph.json")
        logger.info(f"Saved graph to: {save_path}")
        
        # Create new manager and load
        new_manager = TaskGraphManager(self.context)
        loaded = new_manager.load_graph("demo_graph.json")
        
        if loaded:
            logger.info(f"Loaded graph with {len(new_manager.graph.tasks)} tasks")
            logger.info(f"Communities: {len(new_manager.graph.communities)}")
        
    async def run_all_demos(self):
        """Run all demonstration scenarios."""
        try:
            # Start services
            await self.agent_registry.start()
            
            # Run demos
            await self.demo_1_basic_task_creation()
            await asyncio.sleep(1)
            
            await self.demo_2_hierarchical_tasks()
            await asyncio.sleep(1)
            
            await self.demo_3_community_detection()
            await asyncio.sleep(1)
            
            await self.demo_4_architect_to_agents_flow()
            await asyncio.sleep(1)
            
            await self.demo_5_display_modes()
            await asyncio.sleep(1)
            
            await self.demo_6_context_abstraction()
            await asyncio.sleep(1)
            
            await self.demo_7_inter_graph_compatibility()
            await asyncio.sleep(1)
            
            await self.demo_8_persistence()
            
            # Final summary
            logger.info("\n=== Final Summary ===")
            stats = self.task_manager.graph.get_graph_stats()
            logger.info(f"Total tasks created: {len(self.task_manager.graph.tasks)}")
            logger.info(f"Communities formed: {len(self.task_manager.graph.communities)}")
            logger.info(f"Agent registry stats: {self.agent_registry.get_summary_stats()}")
            
        finally:
            # Cleanup
            await self.scheduler.stop()
            await self.agent_registry.stop()


async def main():
    """Main entry point."""
    demo = TaskGraphDemo()
    await demo.run_all_demos()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())