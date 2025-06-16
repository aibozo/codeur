#!/usr/bin/env python3
"""
Demonstration of the fully integrated agent system with task graph and RAG.

This example shows:
1. Creating all integrated agents
2. Architect creating task graph from requirements
3. Request planner breaking down user requests
4. Tasks flowing through the system
5. Agents collaborating via events
6. RAG context being used and updated
7. Task progress tracking
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.agent_factory import create_integrated_agent_system
from src.core.logging import setup_logging

# Set up logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_integrated_system():
    """Demonstrate the fully integrated agent system."""
    print("\n" + "="*80)
    print("FULLY INTEGRATED AGENT SYSTEM DEMONSTRATION")
    print("="*80)
    
    # Step 1: Create integrated agent system
    print("\n1. Creating Integrated Agent System...")
    project_path = "./demo_project"
    Path(project_path).mkdir(exist_ok=True)
    
    system = await create_integrated_agent_system(project_path)
    
    print(f"✓ Created {len(system['agents'])} integrated agents")
    print(f"✓ Task manager initialized")
    print(f"✓ Event bridge active")
    print(f"✓ RAG system: {'available' if system['rag_client'] else 'not available'}")
    
    # Get agents
    architect = system['agents'].get('architect')
    request_planner = system['agents'].get('request_planner')
    coding_agent = system['agents'].get('coding_agent')
    
    # Step 2: Architect creates initial task graph
    print("\n2. Architect Creating Task Graph...")
    requirements = """
    Build a REST API for a todo list application with:
    - User authentication (JWT)
    - CRUD operations for todos
    - User-specific todo lists
    - PostgreSQL database
    - Input validation
    - Error handling
    - Unit tests
    """
    
    # Analyze requirements
    await architect.analyze_project_requirements(requirements)
    print("✓ Requirements analyzed")
    
    # Create task graph
    task_graph = await architect.create_task_graph("todo-api", requirements)
    print(f"✓ Created task graph with {len(task_graph.tasks)} tasks")
    
    # Step 3: Request planner creates detailed plan
    print("\n3. Request Planner Creating Detailed Plan...")
    user_request = "Implement the user authentication system with JWT tokens"
    
    plan = await request_planner.plan_request(user_request, {
        "project_id": "todo-api",
        "task_graph_id": task_graph.project_id
    })
    
    print(f"✓ Created plan with root task: {plan.get('root_task_id')}")
    print(f"✓ Found {plan.get('similar_plans', 0)} similar past plans")
    
    # Step 4: Show task hierarchy
    print("\n4. Task Hierarchy Created:")
    task_manager = system['task_manager']
    
    # Get abstracted state
    state = task_manager.get_abstracted_state()
    print(f"   Total tasks: {state['total_tasks']}")
    print(f"   Communities: {len(state['communities'])}")
    
    for comm_name, comm_data in list(state['communities'].items())[:3]:
        print(f"   - {comm_name}: {comm_data['task_count']} tasks")
    
    # Step 5: Simulate task execution
    print("\n5. Simulating Task Execution...")
    
    # Get ready tasks
    ready_tasks = task_manager.graph.get_ready_tasks()
    print(f"   Ready tasks: {len(ready_tasks)}")
    
    if ready_tasks:
        # Simulate coding agent working on first task
        first_task = ready_tasks[0]
        print(f"   Coding agent working on: {first_task.title}")
        
        # Trigger task assignment
        await system['event_bridge'].emit({
            "type": "task.assigned",
            "task_id": first_task.id,
            "agent_id": "coding_agent"
        })
        
        # Wait a bit for processing
        await asyncio.sleep(1)
        
        # Check task status
        updated_task = task_manager.graph.tasks.get(first_task.id)
        if updated_task:
            print(f"   Task status: {updated_task.status.value}")
    
    # Step 6: Monitor plan execution
    print("\n6. Monitoring Plan Execution...")
    execution_status = await request_planner.monitor_plan_execution(
        plan.get("id", "default")
    )
    
    progress = execution_status.get("progress", {})
    print(f"   Total tasks: {progress.get('total_tasks', 0)}")
    print(f"   Completed: {progress.get('completed', 0)}")
    print(f"   In Progress: {progress.get('in_progress', 0)}")
    print(f"   Progress: {progress.get('percentage', 0):.1f}%")
    
    # Step 7: Show event flow
    print("\n7. Event Flow Example:")
    
    # Set up event listener
    events_received = []
    
    def event_handler(event):
        events_received.append(event)
        
    # Subscribe to task events
    system['event_bridge'].subscribe("task.progress", event_handler)
    system['event_bridge'].subscribe("task.completed", event_handler)
    
    # Emit sample progress event
    await system['event_bridge'].emit({
        "type": "task.progress",
        "task_id": "sample_task",
        "progress": 0.5,
        "message": "Halfway done",
        "agent_id": "coding_agent"
    })
    
    await asyncio.sleep(0.1)  # Let events process
    
    print(f"   Events received: {len(events_received)}")
    for event in events_received:
        print(f"   - {event.get('type')}: {event.get('message', 'N/A')}")
    
    # Step 8: RAG Integration Example
    print("\n8. RAG Integration Example:")
    
    if system['rag_client']:
        # Store a pattern
        await coding_agent._rag_integration.store_pattern(
            pattern="jwt_auth",
            description="JWT authentication implementation",
            example="""
def generate_jwt_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
""",
            tags=["auth", "jwt", "security"]
        )
        print("   ✓ Stored JWT pattern in RAG")
        
        # Search for it
        results = await coding_agent._rag_integration.search_knowledge(
            "JWT token generation",
            filter_type="pattern"
        )
        print(f"   ✓ Found {len(results)} relevant patterns")
    else:
        print("   ⚠️  RAG not available (need OpenAI API key)")
    
    # Step 9: Task graph visualization data
    print("\n9. Task Graph Visualization Data:")
    graph_data = architect.get_current_task_graph() if hasattr(architect, 'get_current_task_graph') else None
    
    if graph_data:
        print(f"   Display mode: {graph_data.get('display_mode', 'unknown')}")
        print(f"   Total nodes: {len(graph_data.get('tasks', {}))}")
        print(f"   Communities: {len(graph_data.get('communities', {}))}")
    
    # Step 10: Cleanup
    print("\n10. Cleanup...")
    await system['factory'].shutdown()
    print("   ✓ All agents shut down")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey Integration Features Demonstrated:")
    print("✓ Agents created with shared task graph and event system")
    print("✓ Architect creates hierarchical task structures")
    print("✓ Request planner breaks down user requests into tasks")
    print("✓ Tasks automatically organized into communities")
    print("✓ Agents communicate via events")
    print("✓ RAG integration for knowledge storage and retrieval")
    print("✓ Task progress tracking and monitoring")
    print("✓ Agent collaboration patterns")


async def main():
    """Run the demonstration."""
    try:
        await demonstrate_integrated_system()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting Integrated Agent System Demo...")
    print("This demo shows the full integration of:")
    print("- Enhanced task graph")
    print("- RAG system")
    print("- Event-driven agent communication")
    print("- Task execution and monitoring")
    
    asyncio.run(main())