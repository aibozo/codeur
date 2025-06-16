#!/usr/bin/env python3
"""
Demo script showing how to use the enhanced task graph system.

This demonstrates:
- Creating hierarchical tasks
- Community detection
- RAG context attachment
- Different display modes
- Task scheduling
"""

import asyncio
import logging
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.task_graph_manager import TaskGraphManager, TaskGraphContext
from src.architect.enhanced_task_graph import TaskPriority, TaskStatus, DisplayMode
from src.core.agent_registry import AgentRegistry
from src.core.task_scheduler import TaskScheduler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_sample_project():
    """Create a sample e-commerce project with tasks."""
    # Create context (without real services for demo)
    context = TaskGraphContext(
        project_id="ecommerce-v2",
        project_path=Path("./demo_project"),
        rag_client=None,  # Would be real RAG client
        agent_registry=None,  # Would be real registry
        scheduler=None  # Would be real scheduler
    )
    
    # Create task graph manager
    manager = TaskGraphManager(context)
    
    # Create main epic: E-commerce Platform
    logger.info("Creating main epic...")
    epic = await manager.create_task_hierarchy(
        epic_title="Build E-commerce Platform",
        epic_description="Create a full-featured online shopping platform with user management, product catalog, and checkout",
        subtasks=[
            {
                'title': "User Authentication System",
                'description': "Implement user registration, login, and session management",
                'agent_type': 'coding_agent',
                'priority': 'high'
            },
            {
                'title': "Product Catalog",
                'description': "Create product listing, search, and filtering functionality",
                'agent_type': 'coding_agent',
                'priority': 'high'
            },
            {
                'title': "Shopping Cart",
                'description': "Implement cart management with add/remove/update functionality",
                'agent_type': 'coding_agent',
                'priority': 'medium'
            },
            {
                'title': "Checkout Process",
                'description': "Create order processing and payment integration",
                'agent_type': 'coding_agent',
                'priority': 'high',
                'dependencies': []  # Will be set after cart is created
            }
        ]
    )
    
    # Create subtasks for authentication
    auth_task_id = None
    for task_id, task in manager.graph.tasks.items():
        if task.title == "User Authentication System":
            auth_task_id = task_id
            break
            
    if auth_task_id:
        logger.info("Creating authentication subtasks...")
        
        # JWT implementation
        jwt_task = await manager.create_task_from_description(
            title="Implement JWT token generation",
            description="Create utilities for generating and validating JWT tokens",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH,
            parent_id=auth_task_id
        )
        
        # User model
        user_model = await manager.create_task_from_description(
            title="Create User model and database schema",
            description="Define User model with fields for authentication",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH,
            parent_id=auth_task_id
        )
        
        # Auth endpoints
        auth_endpoints = await manager.create_task_from_description(
            title="Build authentication API endpoints",
            description="Create /register, /login, /logout endpoints",
            agent_type="coding_agent",
            priority=TaskPriority.MEDIUM,
            parent_id=auth_task_id,
            dependencies={jwt_task.id, user_model.id}
        )
        
        # Tests
        auth_tests = await manager.create_task_from_description(
            title="Write authentication tests",
            description="Create unit and integration tests for auth system",
            agent_type="coding_agent",
            priority=TaskPriority.MEDIUM,
            parent_id=auth_task_id,
            dependencies={auth_endpoints.id}
        )
    
    # Create some database tasks
    logger.info("Creating database tasks...")
    
    db_setup = await manager.create_task_from_description(
        title="Setup PostgreSQL database",
        description="Initialize database with proper configuration and migrations",
        agent_type="coding_agent",
        priority=TaskPriority.CRITICAL
    )
    
    db_models = await manager.create_task_from_description(
        title="Create database models",
        description="Define all database models for products, orders, users",
        agent_type="coding_agent",
        priority=TaskPriority.HIGH,
        dependencies={db_setup.id}
    )
    
    # Create frontend tasks
    logger.info("Creating frontend tasks...")
    
    ui_setup = await manager.create_task_from_description(
        title="Setup React frontend",
        description="Initialize React app with TypeScript and required dependencies",
        agent_type="coding_agent",
        priority=TaskPriority.HIGH
    )
    
    ui_components = await manager.create_task_from_description(
        title="Build reusable UI components",
        description="Create component library with buttons, forms, cards, etc.",
        agent_type="coding_agent",
        priority=TaskPriority.MEDIUM,
        dependencies={ui_setup.id}
    )
    
    # Detect communities
    logger.info("\nDetecting communities...")
    communities = manager.detect_and_create_communities(method="theme")
    
    for community in communities:
        logger.info(f"  Community: {community.name} ({len(community.task_ids)} tasks)")
        
    # Show different views
    logger.info("\nDemonstrating different display modes...")
    
    # Sparse view (default)
    manager.graph.display_mode = DisplayMode.SPARSE
    sparse_tasks = manager.graph.get_display_tasks()
    logger.info(f"  Sparse view: {len(sparse_tasks)} tasks visible")
    
    # Dense view
    manager.graph.display_mode = DisplayMode.DENSE
    dense_tasks = manager.graph.get_display_tasks()
    logger.info(f"  Dense view: {len(dense_tasks)} tasks visible")
    
    # Focused view
    manager.graph.display_mode = DisplayMode.FOCUSED
    manager.graph.set_focused_task(auth_task_id)
    focused_tasks = manager.graph.get_display_tasks()
    logger.info(f"  Focused view (auth): {len(focused_tasks)} tasks visible")
    
    # Get abstracted state
    logger.info("\nGetting abstracted state for architect context...")
    abstracted = manager.get_abstracted_state()
    logger.info(f"  Total tasks: {abstracted['total_tasks']}")
    logger.info(f"  Communities: {len(abstracted['communities'])}")
    logger.info(f"  Top-level tasks: {len(abstracted['top_level_tasks'])}")
    
    # Expand specific task
    if auth_task_id:
        logger.info(f"\nExpanding context for authentication task...")
        expanded = manager.expand_task_context(auth_task_id)
        logger.info(f"  Task: {expanded['task']['title']}")
        logger.info(f"  Subtasks: {len(expanded['task']['subtask_ids'])}")
        if expanded['community']:
            logger.info(f"  Community: {expanded['community']['name']}")
            
    # Save the graph
    logger.info("\nSaving task graph...")
    saved_path = manager.save_graph()
    logger.info(f"  Saved to: {saved_path}")
    
    # Demonstrate loading
    logger.info("\nLoading task graph...")
    new_manager = TaskGraphManager(context)
    if new_manager.load_graph():
        logger.info(f"  Successfully loaded {len(new_manager.graph.tasks)} tasks")
        
    return manager


async def demonstrate_scheduling():
    """Demonstrate task scheduling (with mock services)."""
    logger.info("\n" + "="*60)
    logger.info("DEMONSTRATING TASK SCHEDULING")
    logger.info("="*60)
    
    # Create mock registry and scheduler
    registry = AgentRegistry()
    await registry.start()
    
    # Register some agents
    await registry.register_agent("coding_agent", "gpt-4", ["coding", "testing"])
    await registry.register_agent("architect", "gpt-4", ["planning", "design"])
    
    scheduler = TaskScheduler(registry, max_concurrent_tasks=5)
    await scheduler.start()
    
    # Create context with scheduler
    context = TaskGraphContext(
        project_id="scheduled-project",
        project_path=Path("./scheduled_project"),
        agent_registry=registry,
        scheduler=scheduler
    )
    
    manager = TaskGraphManager(context)
    
    # Create some tasks
    task1 = await manager.create_task_from_description(
        title="Setup project structure",
        description="Initialize project with dependencies",
        priority=TaskPriority.HIGH
    )
    
    task2 = await manager.create_task_from_description(
        title="Implement core features",
        description="Build main functionality",
        priority=TaskPriority.MEDIUM,
        dependencies={task1.id}
    )
    
    task3 = await manager.create_task_from_description(
        title="Add tests",
        description="Write comprehensive tests",
        priority=TaskPriority.MEDIUM,
        dependencies={task2.id}
    )
    
    # Mark first task as ready
    task1.status = TaskStatus.READY
    
    # Schedule ready tasks
    scheduled = await manager.schedule_ready_tasks()
    logger.info(f"  Scheduled {scheduled} tasks")
    
    # Get scheduler status
    status = scheduler.get_scheduler_status()
    logger.info(f"  Active tasks: {status['active_tasks']}")
    logger.info(f"  Queued tasks: {status['queued_tasks']}")
    
    # Wait a bit for simulation
    await asyncio.sleep(2)
    
    # Clean up
    await scheduler.stop()
    await registry.stop()


async def main():
    """Run the demo."""
    logger.info("="*60)
    logger.info("ENHANCED TASK GRAPH DEMO")
    logger.info("="*60)
    
    # Create sample project
    manager = await create_sample_project()
    
    # Demonstrate scheduling
    await demonstrate_scheduling()
    
    logger.info("\nDemo completed!")


if __name__ == "__main__":
    asyncio.run(main())