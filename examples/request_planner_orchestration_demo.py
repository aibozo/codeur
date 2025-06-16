#!/usr/bin/env python3
"""
Demonstration of the Request Planner orchestrating task execution.

This shows how the request planner:
1. Converts user requests into plans
2. Creates hierarchical task graphs
3. Assigns tasks to appropriate agents
4. Monitors execution progress
5. Handles task completion and triggers next tasks
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.agent_factory import IntegratedAgentFactory
from src.core.event_bridge import EventBridge
from src.core.message_bus import MessageBus
from src.core.realtime import RealtimeService
from src.core.settings import Settings
from src.core.integrated_agent_base import AgentContext
from src.request_planner.enhanced_integrated_planner import EnhancedIntegratedRequestPlanner
from src.request_planner.models import ChangeRequest
from src.architect.enhanced_task_graph import TaskStatus
from src.core.logging import setup_logging

# Set up logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def simulate_agent_work(event_bridge: EventBridge, task_manager):
    """Simulate agents working on tasks."""
    
    async def handle_task_assigned(event):
        """Simulate an agent picking up and completing a task."""
        task_id = event.get("task_id")
        agent_id = event.get("agent_id")
        
        if not task_id:
            return
            
        # Get task
        task = task_manager.graph.tasks.get(task_id)
        if not task:
            return
            
        logger.info(f"[{agent_id}] Starting work on: {task.title}")
        
        # Update status to in progress
        task.status = TaskStatus.IN_PROGRESS
        await event_bridge.emit({
            "type": "task.progress",
            "task_id": task_id,
            "agent_id": agent_id,
            "progress": 0.1,
            "message": "Starting task"
        })
        
        # Simulate work (shortened for demo)
        await asyncio.sleep(1)
        
        # Simulate progress updates
        for progress in [0.3, 0.6, 0.9]:
            await event_bridge.emit({
                "type": "task.progress",
                "task_id": task_id,
                "agent_id": agent_id,
                "progress": progress,
                "message": f"Working... {int(progress * 100)}%"
            })
            await asyncio.sleep(0.5)
            
        # Complete task
        task.status = TaskStatus.COMPLETED
        await event_bridge.emit({
            "type": "task.completed",
            "task_id": task_id,
            "agent_id": agent_id,
            "message": f"Completed: {task.title}"
        })
        
        logger.info(f"[{agent_id}] Completed: {task.title}")
        
    # Subscribe to task assignments
    event_bridge.subscribe("task.assigned", handle_task_assigned)
    

async def demonstrate_orchestration():
    """Demonstrate the request planner orchestrating task execution."""
    print("\n" + "="*80)
    print("REQUEST PLANNER ORCHESTRATION DEMONSTRATION")
    print("="*80)
    
    # Step 1: Set up infrastructure
    print("\n1. Setting up infrastructure...")
    settings = Settings()
    message_bus = MessageBus()
    realtime_service = RealtimeService(settings)
    event_bridge = EventBridge(message_bus, realtime_service)
    
    # Create factory
    project_path = Path("./demo_orchestration")
    project_path.mkdir(exist_ok=True)
    
    factory = IntegratedAgentFactory(
        project_path=project_path,
        event_bridge=event_bridge,
        settings=settings
    )
    
    # Step 2: Create enhanced request planner
    print("\n2. Creating Enhanced Request Planner...")
    context = factory.create_agent_context("request_planner")
    planner = EnhancedIntegratedRequestPlanner(context)
    
    # Set up event handlers
    event_bridge.subscribe("task.completed", planner.handle_task_completed)
    
    # Start simulated agents
    await simulate_agent_work(event_bridge, factory.task_manager)
    
    print("✓ Request planner ready")
    print("✓ Task graph manager initialized")
    print("✓ Event system active")
    
    # Step 3: Create a user request
    print("\n3. Processing User Request...")
    user_request = ChangeRequest(
        description="Add user authentication with JWT tokens to the API",
        intent={"type": "add_feature", "feature": "JWT authentication"},
        context={"framework": "FastAPI", "database": "PostgreSQL"}
    )
    
    # Create plan
    plan = planner.create_plan(user_request)
    print(f"✓ Created plan: {plan.id}")
    print(f"✓ Steps: {len(plan.steps)}")
    for i, step in enumerate(plan.steps):
        print(f"   {i+1}. {step.goal} ({step.kind.value})")
    
    # Step 4: Execute plan with task graph
    print("\n4. Executing Plan with Task Graph...")
    execution_info = await planner.execute_plan_with_graph(plan)
    
    print(f"✓ Root task ID: {execution_info['root_task_id']}")
    print(f"✓ Status: {execution_info['status']}")
    
    # Step 5: Show initial task assignments
    print("\n5. Initial Task Assignments:")
    await asyncio.sleep(0.5)  # Let events propagate
    
    ready_tasks = factory.task_manager.graph.get_ready_tasks()
    print(f"✓ Ready tasks: {len(ready_tasks)}")
    for task in ready_tasks[:5]:
        print(f"   - {task.title} → {task.assigned_agent or 'unassigned'}")
    
    # Step 6: Monitor execution progress
    print("\n6. Monitoring Execution Progress...")
    print("   (Simulating agent work...)")
    
    # Track progress
    for i in range(10):
        await asyncio.sleep(2)
        
        # Get execution status
        status = await planner.get_execution_status(plan.id)
        
        print(f"\n   Progress Update {i+1}:")
        print(f"   - Total tasks: {status['total_tasks']}")
        print(f"   - Completed: {status['status_breakdown']['completed']}")
        print(f"   - In Progress: {status['status_breakdown']['in_progress']}")
        print(f"   - Ready: {status['status_breakdown']['ready']}")
        print(f"   - Completion: {status['completion_percentage']:.1f}%")
        
        # Show active tasks
        if status['active_tasks']:
            print("   - Active:")
            for task in status['active_tasks'][:3]:
                print(f"     • {task['title']} ({task['agent']})")
                
        # Check if complete
        if not status['is_executing']:
            print("\n✅ Plan execution completed!")
            break
            
    # Step 7: Show final task graph state
    print("\n7. Final Task Graph State:")
    
    # Get all tasks
    all_tasks = list(factory.task_manager.graph.tasks.values())
    
    # Group by status
    by_status = {}
    for task in all_tasks:
        status = task.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(task)
        
    print(f"✓ Total tasks created: {len(all_tasks)}")
    for status, tasks in by_status.items():
        print(f"   - {status}: {len(tasks)}")
        
    # Show task hierarchy
    print("\n8. Task Hierarchy Created:")
    root_task_id = execution_info['root_task_id']
    root_task = factory.task_manager.graph.tasks.get(root_task_id)
    
    if root_task:
        def print_task_tree(task, indent=0):
            print("  " * indent + f"• {task.title} [{task.status.value}]")
            for subtask_id in task.subtask_ids:
                subtask = factory.task_manager.graph.tasks.get(subtask_id)
                if subtask:
                    print_task_tree(subtask, indent + 1)
                    
        print_task_tree(root_task)
    
    # Step 9: Show event flow
    print("\n9. Event Flow Summary:")
    event_counts = {
        "task.assigned": 0,
        "task.progress": 0, 
        "task.completed": 0
    }
    
    def count_event(event):
        event_type = event.get("type", "")
        if event_type in event_counts:
            event_counts[event_type] += 1
            
    # Subscribe counters
    for event_type in event_counts:
        event_bridge.subscribe(event_type, count_event)
        
    # Wait a bit to collect events
    await asyncio.sleep(2)
    
    print("✓ Events emitted:")
    for event_type, count in event_counts.items():
        print(f"   - {event_type}: {count}")
    
    # Cleanup
    await factory.shutdown()
    
    print("\n" + "="*80)
    print("ORCHESTRATION DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey Capabilities Demonstrated:")
    print("✓ Request planner converts requests into hierarchical task graphs")
    print("✓ Tasks are automatically assigned to appropriate agents")
    print("✓ Execution progress is tracked in real-time")
    print("✓ Completed tasks trigger assignment of dependent tasks")
    print("✓ The system handles complex multi-step workflows")


async def main():
    """Run the demonstration."""
    try:
        await demonstrate_orchestration()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Request Planner Orchestration Demo")
    print("This demonstrates how the request planner orchestrates")
    print("task execution across multiple agents using the task graph.")
    
    asyncio.run(main())