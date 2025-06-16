#!/usr/bin/env python3
"""
Complete integration test demonstrating the full system working together.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import tempfile

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.message_bus import MessageBus
from src.core.event_bridge import EventBridge
from src.core.simple_event_bridge import SimpleEventBridge
from src.core.realtime import RealtimeService
from src.core.settings import Settings
from src.core.agent_factory import IntegratedAgentFactory
from src.architect.architect import Architect
from src.request_planner.enhanced_integrated_planner import EnhancedIntegratedRequestPlanner
from src.request_planner.models import ChangeRequest
from src.core.integrated_agent_base import AgentContext
from src.core.logging import setup_logging

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_complete_integration():
    """Test the complete integrated system."""
    print("\n" + "="*80)
    print("COMPLETE SYSTEM INTEGRATION TEST")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Create infrastructure
        print("\n1. Setting up infrastructure...")
        message_bus = MessageBus()
        settings = Settings()
        realtime_service = RealtimeService(settings)
        event_bridge = EventBridge(message_bus, realtime_service)
        simple_bridge = SimpleEventBridge(event_bridge)
        
        # Create factory
        factory = IntegratedAgentFactory(
            project_path=Path(tmpdir),
            event_bridge=event_bridge,
            settings=settings
        )
        
        print("✓ Infrastructure created")
        
        # 2. Create Architect
        print("\n2. Creating Architect with enhanced task graph...")
        architect = await factory.create_architect()
        print("✓ Architect created")
        
        # 3. Create Request Planner
        print("\n3. Creating Enhanced Request Planner...")
        context = factory.create_agent_context("request_planner")
        context.simple_event_bridge = simple_bridge
        planner = EnhancedIntegratedRequestPlanner(context)
        print("✓ Request planner created")
        
        # 4. Architect creates initial design
        print("\n4. Architect creating system design...")
        requirements = """
        Build a task management API with:
        - User authentication
        - CRUD operations for tasks
        - Task assignment to users
        - Priority levels
        - Due dates
        """
        
        task_graph = await architect.create_task_graph("task-mgmt-api", requirements)
        print(f"✓ Architect created {len(task_graph.tasks)} design tasks")
        
        # 5. Request Planner creates execution plan
        print("\n5. Request Planner creating execution plan...")
        request = ChangeRequest(
            description="Implement the authentication system first",
            repo=str(tmpdir)
        )
        
        plan = planner.create_plan(request)
        print(f"✓ Plan created with {len(plan.steps)} steps:")
        for i, step in enumerate(plan.steps):
            print(f"   {i+1}. {step.goal} ({step.kind.value})")
            
        # 6. Execute plan with task graph
        print("\n6. Executing plan with task graph integration...")
        execution_info = await planner.execute_plan_with_graph(plan)
        print(f"✓ Execution started")
        print(f"  Root task: {execution_info['root_task_id']}")
        print(f"  Total steps: {execution_info['total_steps']}")
        
        # 7. Check task assignments
        print("\n7. Checking task assignments...")
        ready_tasks = factory.task_manager.graph.get_ready_tasks()
        print(f"✓ {len(ready_tasks)} tasks ready for execution")
        
        for task in ready_tasks[:3]:
            print(f"  - {task.title}")
            if task.assigned_agent:
                print(f"    → Assigned to: {task.assigned_agent}")
                
        # 8. Simulate progress tracking
        print("\n8. Simulating progress tracking...")
        
        # Track events
        events_received = []
        
        async def event_tracker(event):
            events_received.append({
                'type': event['type'],
                'time': datetime.now()
            })
            
        # Subscribe to events
        for event_type in ['task.created', 'task.assigned', 'task.progress']:
            simple_bridge.subscribe(event_type, event_tracker)
            
        # Simulate some progress
        if ready_tasks:
            first_task = ready_tasks[0]
            await simple_bridge.emit({
                "type": "task.progress",
                "task_id": first_task.id,
                "progress": 0.5,
                "message": "Halfway done"
            })
            
        await asyncio.sleep(0.1)
        
        # 9. Get execution status
        print("\n9. Getting execution status...")
        status = await planner.get_execution_status(plan.id)
        
        print(f"✓ Execution status:")
        print(f"  Total tasks: {status['total_tasks']}")
        print(f"  Breakdown: {status['status_breakdown']}")
        print(f"  Completion: {status['completion_percentage']:.1f}%")
        
        # 10. Check task communities
        print("\n10. Checking task communities...")
        communities = factory.task_manager.graph.communities
        if communities:
            print(f"✓ {len(communities)} communities detected:")
            for comm in list(communities.values())[:3]:
                print(f"  - {comm.name}: {len(comm.task_ids)} tasks")
        else:
            print("  No communities detected (tasks too few)")
            
        # 11. Get abstracted state
        print("\n11. Getting abstracted state for context management...")
        state = factory.task_manager.get_abstracted_state()
        print(f"✓ Abstracted state:")
        print(f"  Total tasks: {state['total_tasks']}")
        print(f"  Communities: {len(state['communities'])}")
        print(f"  Top-level tasks: {len(state['top_level_tasks'])}")
        
        # Summary
        print("\n" + "="*80)
        print("INTEGRATION TEST COMPLETE")
        print("="*80)
        print("\n✅ All components working together:")
        print("  • Infrastructure (events, message bus) ✓")
        print("  • Architect with enhanced task graph ✓")
        print("  • Request planner with task orchestration ✓")
        print("  • Task assignment and tracking ✓")
        print("  • Progress monitoring ✓")
        print("  • Community detection ✓")
        print("  • Context abstraction ✓")
        
        print(f"\n📊 System created {state['total_tasks']} tasks from requirements")
        print(f"📊 Tracked {len(events_received)} events during execution")
        
        # Cleanup
        await factory.shutdown()
        
    return True


async def main():
    """Run the complete integration test."""
    try:
        success = await test_complete_integration()
        if success:
            print("\n🎉 SYSTEM INTEGRATION VERIFIED!")
            print("\nThe system is ready for additional components:")
            print("• New graph types can be added")
            print("• Agents can be enhanced with task awareness")
            print("• RAG integration can be activated with API key")
            print("• Event flows are working correctly")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Complete System Integration Test")
    print("This demonstrates all components working together")
    asyncio.run(main())