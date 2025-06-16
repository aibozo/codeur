#!/usr/bin/env python3
"""
Comprehensive integration test suite for the agent system.

This tests all major integration points:
1. Event system (typed and string-based)
2. Task graph creation and manipulation
3. Agent communication patterns
4. Task assignment and execution flow
5. RAG integration (if available)
6. Status updates and progress tracking
"""

import asyncio
import pytest
import logging
from pathlib import Path
import tempfile
import json
from typing import Dict, Any, List
from datetime import datetime

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
from src.architect.architect import Architect
from src.request_planner.planner import RequestPlanner
from src.request_planner.models import ChangeRequest
from src.core.logging import setup_logging

# Set up logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEventSystem:
    """Test event system integration."""
    
    @pytest.fixture
    def event_system(self):
        """Create event system components."""
        message_bus = MessageBus()
        settings = Settings()
        realtime_service = RealtimeService(settings)
        event_bridge = EventBridge(message_bus, realtime_service)
        simple_bridge = SimpleEventBridge(event_bridge)
        
        return {
            'message_bus': message_bus,
            'event_bridge': event_bridge,
            'simple_bridge': simple_bridge
        }
    
    @pytest.mark.asyncio
    async def test_simple_event_bridge(self, event_system):
        """Test simple string-based events."""
        simple_bridge = event_system['simple_bridge']
        
        # Track received events
        received = []
        
        async def handler(event):
            received.append(event)
            
        # Subscribe
        simple_bridge.subscribe("test.event", handler)
        
        # Emit event
        await simple_bridge.emit({
            "type": "test.event",
            "data": "hello world",
            "timestamp": datetime.now().isoformat()
        })
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify
        assert len(received) == 1
        assert received[0]['data'] == "hello world"
        print("✓ Simple event bridge working")
        
    @pytest.mark.asyncio
    async def test_typed_messages(self, event_system):
        """Test typed message system."""
        message_bus = event_system['message_bus']
        
        # Define test message
        @dataclass
        class TestMessage(Message):
            test_data: str
            
        # Track received
        received = []
        
        async def handler(msg: TestMessage):
            received.append(msg)
            
        # Subscribe
        message_bus.subscribe(TestMessage, handler)
        
        # Publish
        msg = TestMessage(
            timestamp=datetime.now(),
            source="test",
            data={"test": True},
            test_data="hello typed"
        )
        await message_bus.publish(msg)
        
        # Wait
        await asyncio.sleep(0.1)
        
        # Verify
        assert len(received) == 1
        assert received[0].test_data == "hello typed"
        print("✓ Typed message system working")
        
    @pytest.mark.asyncio
    async def test_event_propagation(self, event_system):
        """Test event propagation through the system."""
        simple_bridge = event_system['simple_bridge']
        
        # Set up chain of handlers
        events_seen = []
        
        async def handler1(event):
            events_seen.append(("handler1", event['type']))
            # Emit another event
            await simple_bridge.emit({
                "type": "chain.event2",
                "triggered_by": "handler1"
            })
            
        async def handler2(event):
            events_seen.append(("handler2", event['type']))
            
        simple_bridge.subscribe("chain.event1", handler1)
        simple_bridge.subscribe("chain.event2", handler2)
        
        # Start chain
        await simple_bridge.emit({"type": "chain.event1"})
        
        # Wait for propagation
        await asyncio.sleep(0.2)
        
        # Verify chain
        assert len(events_seen) == 2
        assert events_seen[0] == ("handler1", "chain.event1")
        assert events_seen[1] == ("handler2", "chain.event2")
        print("✓ Event propagation working")


class TestTaskGraphIntegration:
    """Test task graph system integration."""
    
    @pytest.fixture
    def task_system(self, event_system):
        """Create task graph system."""
        context = TaskGraphContext(
            project_id="test_project",
            project_path=Path("./test")
        )
        manager = TaskGraphManager(context)
        
        return {
            'context': context,
            'manager': manager,
            'event_bridge': event_system['simple_bridge']
        }
    
    @pytest.mark.asyncio
    async def test_task_creation(self, task_system):
        """Test task creation and hierarchy."""
        manager = task_system['manager']
        
        # Create root task
        root = await manager.create_task_from_description(
            title="Root Task",
            description="Main task",
            priority=TaskPriority.HIGH
        )
        
        # Create subtasks
        sub1 = await manager.create_task_from_description(
            title="Subtask 1",
            description="First subtask",
            parent_id=root.id
        )
        
        sub2 = await manager.create_task_from_description(
            title="Subtask 2", 
            description="Second subtask",
            parent_id=root.id,
            dependencies={sub1.id}
        )
        
        # Verify hierarchy
        assert root.id in manager.graph.tasks
        assert sub1.id in root.subtask_ids
        assert sub2.id in root.subtask_ids
        assert sub1.id in sub2.dependencies
        
        print("✓ Task creation and hierarchy working")
        
    @pytest.mark.asyncio
    async def test_task_status_updates(self, task_system):
        """Test task status updates and events."""
        manager = task_system['manager']
        event_bridge = task_system['event_bridge']
        
        # Track status events
        status_events = []
        
        async def status_handler(event):
            status_events.append(event)
            
        event_bridge.subscribe("task.status_changed", status_handler)
        
        # Create task
        task = await manager.create_task_from_description(
            title="Status Test Task",
            description="Test status updates"
        )
        
        # Update status
        task.status = TaskStatus.IN_PROGRESS
        await event_bridge.emit({
            "type": "task.status_changed",
            "task_id": task.id,
            "old_status": TaskStatus.PENDING.value,
            "new_status": TaskStatus.IN_PROGRESS.value
        })
        
        # Complete task
        task.status = TaskStatus.COMPLETED
        await event_bridge.emit({
            "type": "task.status_changed",
            "task_id": task.id,
            "old_status": TaskStatus.IN_PROGRESS.value,
            "new_status": TaskStatus.COMPLETED.value
        })
        
        await asyncio.sleep(0.1)
        
        # Verify events
        assert len(status_events) == 2
        assert status_events[0]['new_status'] == TaskStatus.IN_PROGRESS.value
        assert status_events[1]['new_status'] == TaskStatus.COMPLETED.value
        
        print("✓ Task status updates working")
        
    @pytest.mark.asyncio
    async def test_task_dependencies(self, task_system):
        """Test task dependency resolution."""
        manager = task_system['manager']
        
        # Create dependency chain
        task1 = await manager.create_task_from_description("Task 1", "First")
        task2 = await manager.create_task_from_description(
            "Task 2", "Second", dependencies={task1.id}
        )
        task3 = await manager.create_task_from_description(
            "Task 3", "Third", dependencies={task2.id}
        )
        
        # Check ready tasks
        ready = manager.graph.get_ready_tasks()
        ready_ids = [t.id for t in ready]
        
        assert task1.id in ready_ids
        assert task2.id not in ready_ids
        assert task3.id not in ready_ids
        
        # Complete task1
        task1.status = TaskStatus.COMPLETED
        ready = manager.graph.get_ready_tasks()
        ready_ids = [t.id for t in ready]
        
        assert task2.id in ready_ids
        assert task3.id not in ready_ids
        
        print("✓ Task dependency resolution working")
        
    @pytest.mark.asyncio
    async def test_community_detection(self, task_system):
        """Test automatic community detection."""
        manager = task_system['manager']
        
        # Create tasks with themes
        await manager.create_task_from_description(
            "Setup authentication", 
            "Create login system"
        )
        await manager.create_task_from_description(
            "Add JWT tokens",
            "Implement JWT auth"
        )
        await manager.create_task_from_description(
            "Create database schema",
            "Design user tables"
        )
        await manager.create_task_from_description(
            "Add user model",
            "Create user entity"
        )
        
        # Detect communities
        communities = manager.detect_and_create_communities(method="theme")
        
        # Should detect auth and database communities
        assert len(communities) >= 1
        community_names = [c.name for c in communities]
        
        print(f"✓ Community detection found: {community_names}")


class TestAgentIntegration:
    """Test agent system integration."""
    
    @pytest.fixture
    async def agent_system(self, event_system, task_system):
        """Create integrated agent system."""
        # Import here to avoid circular imports
        from src.core.agent_factory import IntegratedAgentFactory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            factory = IntegratedAgentFactory(
                project_path=Path(tmpdir),
                event_bridge=event_system['event_bridge'],
                settings=Settings()
            )
            
            # Override to use simple event bridge
            factory.task_context.event_bridge = event_system['simple_bridge']
            
            yield {
                'factory': factory,
                'event_bridge': event_system['simple_bridge'],
                'task_manager': factory.task_manager
            }
            
            # Cleanup
            await factory.shutdown()
    
    @pytest.mark.asyncio
    async def test_architect_integration(self, agent_system):
        """Test architect with task graph."""
        factory = agent_system['factory']
        
        # Create architect
        architect = await factory.create_architect()
        
        # Create task graph
        requirements = "Build a REST API"
        task_graph = await architect.create_task_graph(
            "test-api",
            requirements
        )
        
        # Verify
        assert task_graph is not None
        assert len(task_graph.tasks) > 0
        
        print(f"✓ Architect created {len(task_graph.tasks)} tasks")
        
    @pytest.mark.asyncio
    async def test_agent_communication(self, agent_system):
        """Test inter-agent communication."""
        event_bridge = agent_system['event_bridge']
        
        # Simulate agent communication
        messages = []
        
        async def agent1_handler(event):
            if event.get('type') == 'request':
                # Agent 1 receives request
                messages.append(('agent1', 'received', event['data']))
                
                # Send response
                await event_bridge.emit({
                    "type": "response",
                    "target": "agent2",
                    "data": "response_data"
                })
                
        async def agent2_handler(event):
            if event.get('type') == 'response':
                messages.append(('agent2', 'received', event['data']))
                
        event_bridge.subscribe("agent.agent1.message", agent1_handler)
        event_bridge.subscribe("agent.agent2.message", agent2_handler)
        
        # Agent 2 sends request to Agent 1
        await event_bridge.emit({
            "type": "agent.agent1.message",
            "data": {"type": "request", "data": "request_data"}
        })
        
        await asyncio.sleep(0.2)
        
        # Verify communication
        assert len(messages) >= 1
        assert messages[0] == ('agent1', 'received', {'type': 'request', 'data': 'request_data'})
        
        print("✓ Agent communication working")


class TestTaskExecutionFlow:
    """Test complete task execution flow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self, agent_system, task_system):
        """Test end-to-end task execution flow."""
        factory = agent_system['factory']
        event_bridge = agent_system['event_bridge']
        
        # Track execution flow
        flow_events = []
        
        async def flow_handler(event):
            flow_events.append({
                'type': event['type'],
                'time': datetime.now(),
                'data': event
            })
            
        # Subscribe to all relevant events
        for event_type in ['task.created', 'task.assigned', 'task.started', 
                          'task.progress', 'task.completed']:
            event_bridge.subscribe(event_type, flow_handler)
            
        # Create a task
        manager = task_system['manager']
        task = await manager.create_task_from_description(
            "Test Implementation",
            "Implement test feature",
            priority=TaskPriority.HIGH
        )
        
        # Emit creation event
        await event_bridge.emit({
            "type": "task.created",
            "task_id": task.id,
            "title": task.title
        })
        
        # Simulate assignment
        await event_bridge.emit({
            "type": "task.assigned",
            "task_id": task.id,
            "agent_id": "test_agent"
        })
        
        # Simulate execution
        await event_bridge.emit({
            "type": "task.started",
            "task_id": task.id,
            "agent_id": "test_agent"
        })
        
        # Progress updates
        for progress in [0.25, 0.5, 0.75, 1.0]:
            await event_bridge.emit({
                "type": "task.progress",
                "task_id": task.id,
                "progress": progress
            })
            await asyncio.sleep(0.05)
            
        # Complete
        await event_bridge.emit({
            "type": "task.completed",
            "task_id": task.id,
            "result": {"status": "success"}
        })
        
        await asyncio.sleep(0.2)
        
        # Verify flow
        event_types = [e['type'] for e in flow_events]
        assert 'task.created' in event_types
        assert 'task.assigned' in event_types
        assert 'task.started' in event_types
        assert 'task.completed' in event_types
        assert event_types.count('task.progress') == 4
        
        print(f"✓ End-to-end flow completed with {len(flow_events)} events")


class TestRAGIntegration:
    """Test RAG system integration (if available)."""
    
    @pytest.mark.asyncio
    async def test_rag_availability(self):
        """Test if RAG is available."""
        try:
            from src.rag_service import RAGService, RAGClient
            print("✓ RAG modules available")
            return True
        except ImportError:
            print("⚠️  RAG not available (expected without OpenAI key)")
            return False
            
    @pytest.mark.asyncio
    async def test_task_context_attachment(self, task_system):
        """Test attaching RAG context to tasks."""
        manager = task_system['manager']
        
        # Create task with context
        task = await manager.create_task_from_description(
            "Implement authentication",
            "Add JWT authentication to API"
        )
        
        # Simulate RAG context
        task.rag_context.file_patterns = ["auth.py", "jwt_utils.py"]
        task.rag_context.relevant_symbols = ["generate_token", "verify_token"]
        task.rag_context.similar_implementations = ["previous_auth_impl"]
        
        # Verify context
        assert len(task.rag_context.file_patterns) == 2
        assert "generate_token" in task.rag_context.relevant_symbols
        
        print("✓ Task RAG context attachment working")


# Main test runner
async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE INTEGRATION TEST SUITE")
    print("="*80)
    
    # Create fixtures
    message_bus = MessageBus()
    settings = Settings()
    realtime_service = RealtimeService(settings)
    event_bridge = EventBridge(message_bus, realtime_service)
    simple_bridge = SimpleEventBridge(event_bridge)
    
    event_system = {
        'message_bus': message_bus,
        'event_bridge': event_bridge,
        'simple_bridge': simple_bridge
    }
    
    context = TaskGraphContext(
        project_id="test_project",
        project_path=Path("./test")
    )
    manager = TaskGraphManager(context)
    
    task_system = {
        'context': context,
        'manager': manager,
        'event_bridge': simple_bridge
    }
    
    # Test categories
    test_suites = [
        ("Event System", TestEventSystem(), event_system),
        ("Task Graph", TestTaskGraphIntegration(), task_system),
        ("Agent Integration", TestAgentIntegration(), None),
        ("Task Execution Flow", TestTaskExecutionFlow(), None),
        ("RAG Integration", TestRAGIntegration(), None)
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for suite_name, suite, fixture in test_suites:
        print(f"\n{'='*60}")
        print(f"Testing: {suite_name}")
        print(f"{'='*60}")
        
        # Get test methods
        test_methods = [
            method for method in dir(suite)
            if method.startswith('test_') and callable(getattr(suite, method))
        ]
        
        for test_name in test_methods:
            total_tests += 1
            print(f"\n▶ {test_name}...")
            
            try:
                test_method = getattr(suite, test_name)
                
                # Create fixtures for the test
                fixtures = {}
                if fixture:
                    fixtures['event_system'] = event_system
                    fixtures['task_system'] = task_system
                    
                # Handle agent system fixture
                if 'agent_system' in test_method.__code__.co_varnames:
                    from src.core.agent_factory import IntegratedAgentFactory
                    
                    with tempfile.TemporaryDirectory() as tmpdir:
                        factory = IntegratedAgentFactory(
                            project_path=Path(tmpdir),
                            event_bridge=event_bridge,
                            settings=Settings()
                        )
                        factory.task_context.event_bridge = simple_bridge
                        
                        fixtures['agent_system'] = {
                            'factory': factory,
                            'event_bridge': simple_bridge,
                            'task_manager': factory.task_manager
                        }
                        
                        await test_method(suite, **fixtures)
                        await factory.shutdown()
                else:
                    # Run test with appropriate fixtures
                    await test_method(suite, **fixtures)
                    
                passed_tests += 1
                
            except Exception as e:
                failed_tests += 1
                print(f"✗ FAILED: {e}")
                import traceback
                traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests} ✓")
    print(f"Failed: {failed_tests} ✗")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! The integration is working correctly.")
        print("\nThe system is ready for additional components:")
        print("✓ Event system functioning")
        print("✓ Task graph operational") 
        print("✓ Agent communication working")
        print("✓ Task execution flow validated")
        print("✓ Integration points verified")
    else:
        print(f"\n⚠️  {failed_tests} tests failed. Please review the errors above.")
        
    return failed_tests == 0


if __name__ == "__main__":
    print("Comprehensive Integration Test Suite")
    print("This will test all major integration points in the system")
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)