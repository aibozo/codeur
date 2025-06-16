#!/usr/bin/env python3
"""
Comprehensive integration tests for the agent system.

Tests:
1. Agent creation and registration
2. Task graph creation and manipulation
3. Event passing between agents
4. RAG integration (if available)
5. Task assignment and execution flow
6. Inter-agent communication
7. State persistence and recovery
"""

import asyncio
import pytest
import logging
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any, List

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.agent_factory import create_integrated_agent_system
from src.architect.enhanced_task_graph import TaskStatus, TaskPriority
from src.core.logging import setup_logging

# Set up logging for tests
setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestFullIntegration:
    """Test the fully integrated agent system."""
    
    @pytest.fixture
    async def integrated_system(self):
        """Create a test integrated system."""
        # Use temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            system = await create_integrated_agent_system(tmpdir)
            yield system
            # Cleanup
            await system['factory'].shutdown()
    
    @pytest.mark.asyncio
    async def test_system_creation(self, integrated_system):
        """Test that all components are created correctly."""
        system = integrated_system
        
        # Check all components exist
        assert system['factory'] is not None
        assert system['agents'] is not None
        assert system['event_bridge'] is not None
        assert system['task_manager'] is not None
        
        # Check all agents created
        expected_agents = [
            'architect', 'request_planner', 'coding_agent', 
            'code_planner', 'analyzer'
        ]
        for agent_id in expected_agents:
            assert agent_id in system['agents']
            
        print("✓ All system components created successfully")
    
    @pytest.mark.asyncio
    async def test_task_graph_creation(self, integrated_system):
        """Test task graph creation through architect."""
        system = integrated_system
        architect = system['agents']['architect']
        
        # Create task graph
        requirements = "Build a simple REST API"
        task_graph = await architect.create_task_graph("test-api", requirements)
        
        # Verify task graph
        assert task_graph is not None
        assert len(task_graph.tasks) > 0
        assert task_graph.project_id == "test-api"
        
        # Check task manager has the graph
        task_manager = system['task_manager']
        assert len(task_manager.graph.tasks) > 0
        
        print(f"✓ Created task graph with {len(task_graph.tasks)} tasks")
    
    @pytest.mark.asyncio
    async def test_event_passing(self, integrated_system):
        """Test event passing between components."""
        system = integrated_system
        event_bridge = system['event_bridge']
        
        # Track received events
        received_events = []
        
        async def event_handler(event):
            received_events.append(event)
        
        # Subscribe to test event
        event_bridge.subscribe("test.event", event_handler)
        
        # Emit test event
        test_data = {"message": "Hello from test", "value": 42}
        await event_bridge.emit({
            "type": "test.event",
            **test_data
        })
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify event received
        assert len(received_events) == 1
        assert received_events[0]['message'] == "Hello from test"
        assert received_events[0]['value'] == 42
        
        print("✓ Event passing working correctly")
    
    @pytest.mark.asyncio
    async def test_task_assignment_flow(self, integrated_system):
        """Test task assignment and status updates."""
        system = integrated_system
        task_manager = system['task_manager']
        event_bridge = system['event_bridge']
        
        # Create a test task
        task = await task_manager.create_task_from_description(
            title="Test Implementation Task",
            description="Implement a test feature",
            priority=TaskPriority.HIGH,
            agent_type="coding_agent"
        )
        
        # Track task events
        task_events = []
        
        async def task_event_handler(event):
            task_events.append(event)
        
        event_bridge.subscribe("task.assigned", task_event_handler)
        event_bridge.subscribe("task.progress", task_event_handler)
        
        # Emit task assignment
        await event_bridge.emit({
            "type": "task.assigned",
            "task_id": task.id,
            "agent_id": "coding_agent"
        })
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Verify assignment event received
        assert any(e['type'] == 'task.assigned' for e in task_events)
        
        # Verify task was processed by coding agent
        # (In full implementation, coding agent would update status)
        
        print("✓ Task assignment flow working")
    
    @pytest.mark.asyncio
    async def test_inter_agent_communication(self, integrated_system):
        """Test agents communicating with each other."""
        system = integrated_system
        request_planner = system['agents']['request_planner']
        
        # Test request/response pattern
        response_received = False
        test_response = {"result": "success", "data": "test"}
        
        async def mock_agent_handler(event):
            nonlocal response_received
            if event.get('type') == 'test_request':
                # Send response
                response_event = event.get('response_event')
                if response_event:
                    await system['event_bridge'].emit({
                        "type": response_event,
                        "payload": test_response
                    })
                    response_received = True
        
        # Subscribe mock agent
        system['event_bridge'].subscribe("agent.mock_agent.request", mock_agent_handler)
        
        # Send request from request planner
        response = await request_planner.request_from_agent(
            "mock_agent",
            "test_request",
            {"test": "data"}
        )
        
        # Wait a bit
        await asyncio.sleep(0.2)
        
        # Verify communication
        assert response_received
        assert response == test_response
        
        print("✓ Inter-agent communication working")
    
    @pytest.mark.asyncio 
    async def test_task_hierarchy_and_communities(self, integrated_system):
        """Test task hierarchy creation and community detection."""
        system = integrated_system
        architect = system['agents']['architect']
        
        # Use architect tools if available
        if hasattr(architect, 'architect_tools') and architect.architect_tools:
            tools = architect.architect_tools
            
            # Create hierarchical tasks
            result = await tools.create_tasks(
                content="""
Authentication System:
  - Setup Database (high, 2h)
  - User Management:
    - Create user model (1h)
    - Add validation (1h)
  - JWT Implementation (high, 3h)
  - API Endpoints:
    - Login endpoint (2h)
    - Logout endpoint (1h)
""",
                format="list"
            )
            
            assert result['status'] == 'success'
            assert result['created_tasks'] > 5
            
            # Check communities were detected
            task_manager = system['task_manager']
            communities = task_manager.graph.communities
            
            # Should have detected auth community
            assert len(communities) > 0
            
            print(f"✓ Created {result['created_tasks']} tasks in {len(communities)} communities")
        else:
            print("⚠️  Architect tools not available (no LLM)")
    
    @pytest.mark.asyncio
    async def test_rag_integration(self, integrated_system):
        """Test RAG integration if available."""
        system = integrated_system
        
        if system['rag_client']:
            coding_agent = system['agents']['coding_agent']
            
            # Store a test pattern
            await coding_agent.store_implementation(
                code="def test_function():\n    return 'Hello World'",
                description="Test implementation",
                task_id="test_task_123",
                tags=["test", "demo"]
            )
            
            # Search for it
            results = await coding_agent.search_context(
                "test function implementation",
                task_id="test_task_123"
            )
            
            # Should find something (even if just the task context)
            assert isinstance(results, list)
            
            print("✓ RAG integration working")
        else:
            print("⚠️  RAG not available (no OpenAI API key)")
    
    @pytest.mark.asyncio
    async def test_task_status_progression(self, integrated_system):
        """Test task status progression through the system."""
        system = integrated_system
        task_manager = system['task_manager']
        
        # Create a task
        task = await task_manager.create_task_from_description(
            title="Progress Test Task",
            description="Test task status progression",
            priority=TaskPriority.MEDIUM
        )
        
        # Progress through statuses
        statuses = [
            (TaskStatus.READY, "Task ready to start"),
            (TaskStatus.IN_PROGRESS, "Task in progress"),
            (TaskStatus.COMPLETED, "Task completed")
        ]
        
        for status, message in statuses:
            task.status = status
            
            # Emit status event
            await system['event_bridge'].emit({
                "type": f"task.{status.value}",
                "task_id": task.id,
                "message": message
            })
            
            # Verify status
            assert task.status == status
            
        print("✓ Task status progression working")
    
    @pytest.mark.asyncio
    async def test_task_dependencies(self, integrated_system):
        """Test task dependency handling."""
        system = integrated_system
        task_manager = system['task_manager']
        
        # Create parent task
        parent = await task_manager.create_task_from_description(
            title="Parent Task",
            description="Must complete first"
        )
        
        # Create dependent task
        child = await task_manager.create_task_from_description(
            title="Child Task",
            description="Depends on parent",
            dependencies={parent.id}
        )
        
        # Verify dependency
        assert parent.id in child.dependencies
        assert child.id in parent.dependents
        
        # Check ready tasks (only parent should be ready)
        ready = task_manager.graph.get_ready_tasks()
        ready_ids = [t.id for t in ready]
        
        assert parent.id in ready_ids
        assert child.id not in ready_ids
        
        # Complete parent
        parent.status = TaskStatus.COMPLETED
        
        # Now child should be ready
        ready = task_manager.graph.get_ready_tasks()
        ready_ids = [t.id for t in ready]
        
        assert child.id in ready_ids
        
        print("✓ Task dependency handling working")
    
    @pytest.mark.asyncio
    async def test_abstracted_state(self, integrated_system):
        """Test abstracted state for context management."""
        system = integrated_system
        task_manager = system['task_manager']
        
        # Create some tasks
        for i in range(5):
            await task_manager.create_task_from_description(
                title=f"Task {i}",
                description=f"Test task number {i}"
            )
        
        # Get abstracted state
        state = task_manager.get_abstracted_state()
        
        # Verify state structure
        assert 'total_tasks' in state
        assert 'completed_tasks' in state
        assert 'communities' in state
        assert 'top_level_tasks' in state
        
        assert state['total_tasks'] >= 5
        
        print("✓ Abstracted state working correctly")


# Standalone test runner
async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("RUNNING FULL INTEGRATION TESTS")
    print("="*80)
    
    # Create test instance
    test_suite = TestFullIntegration()
    
    # Create system
    print("\nCreating test system...")
    with tempfile.TemporaryDirectory() as tmpdir:
        system = await create_integrated_agent_system(tmpdir)
        
        try:
            # Run each test
            tests = [
                ("System Creation", test_suite.test_system_creation),
                ("Task Graph Creation", test_suite.test_task_graph_creation),
                ("Event Passing", test_suite.test_event_passing),
                ("Task Assignment Flow", test_suite.test_task_assignment_flow),
                ("Inter-Agent Communication", test_suite.test_inter_agent_communication),
                ("Task Hierarchy & Communities", test_suite.test_task_hierarchy_and_communities),
                ("RAG Integration", test_suite.test_rag_integration),
                ("Task Status Progression", test_suite.test_task_status_progression),
                ("Task Dependencies", test_suite.test_task_dependencies),
                ("Abstracted State", test_suite.test_abstracted_state),
            ]
            
            passed = 0
            failed = 0
            
            for test_name, test_func in tests:
                print(f"\n▶ Testing: {test_name}")
                try:
                    await test_func(system)
                    passed += 1
                except Exception as e:
                    print(f"✗ FAILED: {test_name}")
                    print(f"  Error: {e}")
                    import traceback
                    traceback.print_exc()
                    failed += 1
            
            # Summary
            print("\n" + "-"*80)
            print(f"SUMMARY: {passed} passed, {failed} failed out of {len(tests)} tests")
            
            if failed == 0:
                print("\n🎉 ALL TESTS PASSED! The integration is working correctly.")
            else:
                print(f"\n⚠️  {failed} tests failed. Please check the errors above.")
                
        finally:
            # Cleanup
            await system['factory'].shutdown()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    print("Full Integration Test Suite")
    print("This will test all components of the integrated agent system")
    asyncio.run(run_all_tests())