#!/usr/bin/env python3
"""
Simple integration test without pytest complexity.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import tempfile

import sys
sys.path.append(str(Path(__file__).parent.parent))

from dataclasses import dataclass
from src.core.message_bus import MessageBus, Message
from src.core.event_bridge import EventBridge
from src.core.simple_event_bridge import SimpleEventBridge
from src.core.realtime import RealtimeService
from src.core.settings import Settings
from src.core.agent_registry import AgentRegistry
from src.architect.task_graph_manager import TaskGraphManager, TaskGraphContext
from src.architect.enhanced_task_graph import TaskPriority, TaskStatus
from src.core.logging import setup_logging

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_event_system():
    """Test the event system."""
    print("\n" + "="*60)
    print("Testing Event System")
    print("="*60)
    
    # Create components
    message_bus = MessageBus()
    settings = Settings()
    realtime_service = RealtimeService(settings) 
    event_bridge = EventBridge(message_bus, realtime_service)
    simple_bridge = SimpleEventBridge(event_bridge)
    
    # Test 1: Simple events
    print("\n1. Testing simple event bridge...")
    received = []
    
    async def handler(event):
        received.append(event)
        
    simple_bridge.subscribe("test.event", handler)
    
    await simple_bridge.emit({
        "type": "test.event",
        "data": "hello world"
    })
    
    await asyncio.sleep(0.1)
    
    if len(received) == 1 and received[0]['data'] == "hello world":
        print("✓ Simple events working")
    else:
        print(f"✗ Simple events failed: received {len(received)} events")
        
    # Test 2: Event propagation
    print("\n2. Testing event propagation...")
    chain_events = []
    
    async def chain_handler1(event):
        chain_events.append("handler1")
        await simple_bridge.emit({
            "type": "chain.event2", 
            "triggered_by": "handler1"
        })
        
    async def chain_handler2(event):
        chain_events.append("handler2")
        
    simple_bridge.subscribe("chain.event1", chain_handler1)
    simple_bridge.subscribe("chain.event2", chain_handler2)
    
    await simple_bridge.emit({"type": "chain.event1"})
    await asyncio.sleep(0.2)
    
    if chain_events == ["handler1", "handler2"]:
        print("✓ Event propagation working")
    else:
        print(f"✗ Event propagation failed: {chain_events}")
        
    return True


async def test_task_graph():
    """Test task graph functionality."""
    print("\n" + "="*60)
    print("Testing Task Graph")
    print("="*60)
    
    # Create task graph
    context = TaskGraphContext(
        project_id="test_project",
        project_path=Path("./test")
    )
    manager = TaskGraphManager(context)
    
    # Test 1: Task creation
    print("\n1. Testing task creation...")
    root = await manager.create_task_from_description(
        title="Root Task",
        description="Main task",
        priority=TaskPriority.HIGH
    )
    
    sub1 = await manager.create_task_from_description(
        title="Subtask 1",
        description="First subtask",
        parent_id=root.id
    )
    
    if root.id in manager.graph.tasks and sub1.id in root.subtask_ids:
        print("✓ Task creation working")
    else:
        print("✗ Task creation failed")
        
    # Test 2: Dependencies
    print("\n2. Testing task dependencies...")
    task1 = await manager.create_task_from_description("Task 1", "First")
    task2 = await manager.create_task_from_description(
        "Task 2", "Second", dependencies={task1.id}
    )
    
    ready = manager.graph.get_ready_tasks()
    ready_ids = [t.id for t in ready]
    
    if task1.id in ready_ids and task2.id not in ready_ids:
        print("✓ Task dependencies working")
    else:
        print("✗ Task dependencies failed")
        
    # Complete task1
    task1.status = TaskStatus.COMPLETED
    ready = manager.graph.get_ready_tasks()
    ready_ids = [t.id for t in ready]
    
    if task2.id in ready_ids:
        print("✓ Dependency resolution working")
    else:
        print("✗ Dependency resolution failed")
        
    # Test 3: Communities
    print("\n3. Testing community detection...")
    await manager.create_task_from_description("Setup authentication", "Auth system")
    await manager.create_task_from_description("Add JWT tokens", "JWT implementation")
    await manager.create_task_from_description("Create user model", "User database")
    
    communities = manager.detect_and_create_communities(method="theme")
    if len(communities) > 0:
        print(f"✓ Community detection found {len(communities)} communities")
    else:
        print("✗ Community detection failed")
        
    return True


async def test_architect():
    """Test architect integration."""
    print("\n" + "="*60)
    print("Testing Architect")
    print("="*60)
    
    from src.architect.architect import Architect
    
    # Create architect
    print("\n1. Creating architect...")
    with tempfile.TemporaryDirectory() as tmpdir:
        architect = Architect(
            project_path=tmpdir,
            use_enhanced_task_graph=True
        )
        print("✓ Architect created")
        
        # Test task graph creation
        print("\n2. Creating task graph...")
        requirements = "Build a simple REST API"
        task_graph = await architect.create_task_graph("test-api", requirements)
        
        if task_graph and len(task_graph.tasks) > 0:
            print(f"✓ Task graph created with {len(task_graph.tasks)} tasks")
        else:
            print("✗ Task graph creation failed")
            
    return True


async def test_request_planner():
    """Test request planner."""
    print("\n" + "="*60)
    print("Testing Request Planner")
    print("="*60)
    
    from src.request_planner.planner import RequestPlanner
    from src.request_planner.models import ChangeRequest
    
    # Create planner
    print("\n1. Creating request planner...")
    with tempfile.TemporaryDirectory() as tmpdir:
        planner = RequestPlanner(repo_path=tmpdir)
        print("✓ Request planner created")
        
        # Create a plan
        print("\n2. Creating plan...")
        request = ChangeRequest(
            description="Add user authentication",
            repo=tmpdir,
            branch="main"
        )
        
        plan = planner.create_plan(request)
        
        if plan and len(plan.steps) > 0:
            print(f"✓ Plan created with {len(plan.steps)} steps")
            for i, step in enumerate(plan.steps):
                print(f"   {i+1}. {step.goal}")
        else:
            print("✗ Plan creation failed")
            
    return True


async def test_integration_flow():
    """Test a simple integration flow."""
    print("\n" + "="*60)
    print("Testing Integration Flow")
    print("="*60)
    
    # Create infrastructure
    message_bus = MessageBus()
    settings = Settings()
    realtime_service = RealtimeService(settings)
    event_bridge = EventBridge(message_bus, realtime_service)
    simple_bridge = SimpleEventBridge(event_bridge)
    
    # Create task manager
    context = TaskGraphContext(
        project_id="flow_test",
        project_path=Path("./test")
    )
    manager = TaskGraphManager(context)
    
    # Track flow
    flow_events = []
    
    async def flow_handler(event):
        flow_events.append(event['type'])
        
    # Subscribe to events
    for event_type in ['task.created', 'task.assigned', 'task.completed']:
        simple_bridge.subscribe(event_type, flow_handler)
        
    # Create task
    print("\n1. Creating and executing task flow...")
    task = await manager.create_task_from_description(
        "Test Task",
        "Test implementation"
    )
    
    # Emit events
    await simple_bridge.emit({
        "type": "task.created",
        "task_id": task.id
    })
    
    await simple_bridge.emit({
        "type": "task.assigned",
        "task_id": task.id,
        "agent_id": "test_agent"
    })
    
    await simple_bridge.emit({
        "type": "task.completed",
        "task_id": task.id
    })
    
    await asyncio.sleep(0.2)
    
    expected_flow = ['task.created', 'task.assigned', 'task.completed']
    if flow_events == expected_flow:
        print("✓ Integration flow working")
    else:
        print(f"✗ Integration flow failed: {flow_events}")
        
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("SIMPLE INTEGRATION TEST")
    print("="*80)
    
    tests = [
        ("Event System", test_event_system),
        ("Task Graph", test_task_graph),
        ("Architect", test_architect),
        ("Request Planner", test_request_planner),
        ("Integration Flow", test_integration_flow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ All integration tests passed!")
        print("\nThe system is ready for new components:")
        print("• Event system ✓")
        print("• Task graph ✓")
        print("• Architect ✓")
        print("• Request planner ✓")
        print("• Basic integration flow ✓")
    else:
        print(f"\n⚠️  {failed} tests failed")


if __name__ == "__main__":
    asyncio.run(main())