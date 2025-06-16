#!/usr/bin/env python3
"""
Basic integration test to verify core components work.
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

async def test_basic_integration():
    """Test basic integration components."""
    print("Testing Basic Integration")
    print("="*50)
    
    # Test 1: Import core modules
    print("\n1. Testing imports...")
    try:
        from src.core.event_bridge import EventBridge
        from src.core.message_bus import MessageBus
        from src.core.realtime import RealtimeService
        from src.core.settings import Settings
        print("✓ Core imports successful")
    except Exception as e:
        print(f"✗ Core import failed: {e}")
        return
        
    # Test 2: Create basic infrastructure
    print("\n2. Creating basic infrastructure...")
    try:
        settings = Settings()
        message_bus = MessageBus()
        realtime_service = RealtimeService(settings)
        event_bridge = EventBridge(message_bus, realtime_service)
        print("✓ Infrastructure created")
    except Exception as e:
        print(f"✗ Infrastructure creation failed: {e}")
        return
        
    # Test 3: Test event system
    print("\n3. Testing event system...")
    received = []
    
    async def handler(event):
        received.append(event)
        
    event_bridge.subscribe("test.event", handler)
    await event_bridge.emit({"type": "test.event", "data": "hello"})
    await asyncio.sleep(0.1)
    
    if received:
        print(f"✓ Event system working: received {len(received)} events")
    else:
        print("✗ Event system not working")
        
    # Test 4: Import task graph
    print("\n4. Testing task graph imports...")
    try:
        from src.architect.task_graph_manager import TaskGraphManager, TaskGraphContext
        from src.architect.enhanced_task_graph import EnhancedTaskGraph
        print("✓ Task graph imports successful")
    except Exception as e:
        print(f"✗ Task graph import failed: {e}")
        return
        
    # Test 5: Create task graph
    print("\n5. Creating task graph...")
    try:
        context = TaskGraphContext(
            project_id="test",
            project_path=Path("./test"),
            event_bridge=event_bridge
        )
        manager = TaskGraphManager(context)
        print(f"✓ Task graph created")
    except Exception as e:
        print(f"✗ Task graph creation failed: {e}")
        return
        
    # Test 6: Test architect
    print("\n6. Testing architect...")
    try:
        from src.architect.architect import Architect
        architect = Architect(
            project_path="./test",
            use_enhanced_task_graph=True
        )
        print("✓ Architect created")
    except Exception as e:
        print(f"✗ Architect creation failed: {e}")
        
    # Test 7: Test request planner
    print("\n7. Testing request planner...")
    try:
        from src.request_planner.planner import RequestPlanner
        planner = RequestPlanner(repo_path="./test")
        print("✓ Request planner created")
    except Exception as e:
        print(f"✗ Request planner creation failed: {e}")
        
    print("\n" + "="*50)
    print("Basic Integration Test Complete")

if __name__ == "__main__":
    asyncio.run(test_basic_integration())