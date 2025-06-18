#!/usr/bin/env python3
"""
Stress Test: Todo List Application (Architect-Only)
Tests the complete pipeline from architect to execution with session logging.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone
import uuid

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect import Architect
from src.core.session_logger import SessionLogger, EventType
from src.core.event_bridge import EventBridge, MessageBus
from src.core.task_scheduler_enhanced import PlanBasedTaskScheduler
from src.core.agent_registry import AgentRegistry
from src.rag_service import AdaptiveRAGService

# Test specification
TEST_SPEC = {
    "name": "Todo List App",
    "phase": 1,
    "complexity": "BASIC",
    "description": """
        A todo list application that tests:
        - Multi-file code organization
        - Data persistence with JSON
        - More complex UI with list management
        - Event handling and state management
    """,
    "requirements": """
Create a command-line todo list application with the following features:
- src/todo.py - Main application file with TodoList class
- src/storage.py - JSON file storage for persistence
- src/__main__.py - Entry point that provides CLI interface
- Features to implement:
  - Add todo items with description
  - List all todos with numbers
  - Mark todos as complete
  - Delete todos by number
  - Save/load from todos.json file
- Use argparse for command-line arguments
- Commands: add, list, complete, delete
Example usage:
  python -m src add "Buy groceries"
  python -m src list
  python -m src complete 1
  python -m src delete 1"""
}

async def run_todo_list_architect_test():
    """Run Todo List test using only the Architect (proper pipeline)."""
    
    # Create test directory
    test_output_dir = Path(__file__).parent.parent / "test_output"
    test_output_dir.mkdir(exist_ok=True)
    
    project_path = test_output_dir / "todo_list_architect_test"
    if project_path.exists():
        shutil.rmtree(project_path)
    project_path.mkdir(parents=True)
    
    # Also clean any stale lock files
    import glob
    for lockfile in glob.glob(str(test_output_dir / "*.lock")):
        try:
            os.remove(lockfile)
        except:
            pass
    
    print("=" * 80)
    print(f"STRESS TEST: {TEST_SPEC['name']} (Architect-Only Pipeline)")
    print(f"Phase: {TEST_SPEC['phase']} | Complexity: {TEST_SPEC['complexity']}")
    print("=" * 80)
    
    # Setup basic project structure
    print("\n1. Setting up project structure...")
    src_dir = project_path / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").touch()
    
    tests_dir = project_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").touch()
    
    # Initialize git repository
    print("   Initializing git repository...")
    os.system(f"cd {project_path} && git init -q")
    os.system(f"cd {project_path} && git config user.email 'test@example.com'")
    os.system(f"cd {project_path} && git config user.name 'Test User'")
    # Create initial commit so we have a branch
    os.system(f"cd {project_path} && git add .")
    os.system(f"cd {project_path} && git commit -q -m 'Initial commit'")
    
    # Create session logger
    print("\n2. Initializing session logging...")
    session_id = str(uuid.uuid4())
    log_dir = Path(".agent_logs/stress_tests")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    session_logger = SessionLogger(
        session_id=session_id,
        output_dir=log_dir
    )
    print(f"   Session ID: {session_id}")
    
    # Initialize services
    print("\n3. Initializing services...")
    
    # Create message bus
    message_bus = MessageBus()
    
    # Mock realtime service
    class MockRealtimeService:
        async def save_job_state(self, job_id, state):
            pass
        
        class ConnectionManager:
            async def broadcast(self, message, topic=None):
                pass
        
        connection_manager = ConnectionManager()
    
    realtime_service = MockRealtimeService()
    
    # Create event bridge with session logger
    event_bridge = EventBridge(
        message_bus=message_bus,
        realtime_service=realtime_service,
        session_logger=session_logger
    )
    
    # Initialize RAG service
    rag_service = AdaptiveRAGService(
        persist_directory=str(project_path / ".rag"),
        repo_path=str(project_path)
    )
    
    # Initialize agent registry
    agent_registry = AgentRegistry()
    
    # Initialize git workflow  
    print("\n4. Initializing git workflow...")
    from src.core.git_workflow import GitWorkflow
    git_workflow = GitWorkflow(
        repo_path=str(project_path),
        event_bridge=event_bridge
    )
    # Initialize session
    git_workflow.initialize_session(session_id=session_id)
    print("   ✓ Git workflow initialized")
    
    # Initialize task scheduler
    print("\n5. Initializing task scheduler...")
    task_scheduler = PlanBasedTaskScheduler(
        agent_registry=agent_registry,
        max_concurrent_tasks=32,  # Allow up to 32 concurrent tasks (matching max coding agents)
        scheduling_interval=1.0   # Check more frequently for better responsiveness
    )
    task_scheduler.event_bridge = event_bridge
    task_scheduler.message_bus = message_bus
    task_scheduler.project_path = project_path
    task_scheduler.git_workflow = git_workflow
    
    # Subscribe to events after setting message_bus
    task_scheduler._subscribe_to_plan_events()
    
    # Start the scheduler
    await task_scheduler.start()
    print("   ✓ Task scheduler started")
    
    # Initialize Symbol Registry
    print("\n5. Initializing Symbol Registry...")
    from src.symbol_registry.embedded import get_embedded_srm
    symbol_registry = get_embedded_srm(project_path)
    await symbol_registry.initialize()
    print("   ✓ Symbol Registry initialized")
    
    # Create architect with event system
    print("\n6. Creating Architect with event system...")
    architect = Architect(
        project_path=str(project_path),
        rag_service=rag_service,
        use_enhanced_task_graph=True,
        event_bridge=event_bridge,
        message_bus=message_bus,
        symbol_registry=symbol_registry
    )
    architect.session_logger = session_logger
    
    if not architect.llm_client:
        print("   ⚠️  No LLM client available - will use mock tasks")
    else:
        print("   ✓ Architect created with LLM support")
    
    # Process the request through architect
    print("\n7. Processing request through Architect...")
    try:
        # This is the ONLY interaction with the system
        result = await architect.process_request(TEST_SPEC["requirements"])
        
        print(f"\n   Result: {result['status']}")
        print(f"   Tasks in plan: {result['task_count']}")
        print(f"   Message: {result['message']}")
        
        if result['status'] == 'success' and 'plan' in result:
            print("\n   Generated Plan:")
            print("   " + "-" * 60)
            # Show first 500 chars of plan
            plan_preview = result['plan'][:500] + "..." if len(result['plan']) > 500 else result['plan']
            for line in plan_preview.split('\n'):
                print(f"   {line}")
        
    except Exception as e:
        print(f"\n   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Wait for task execution with periodic checks
    print("\n8. Waiting for task execution (press Ctrl+C to stop)...")
    print("   This may take several minutes as agents work through the tasks...")
    
    elapsed_time = 0
    check_interval = 10  # Check every 10 seconds
    max_idle_iterations = 30  # Stop after 5 minutes of no activity
    idle_iterations = 0
    last_queue_size = None
    last_active_tasks = None
    
    while True:
        await asyncio.sleep(check_interval)
        elapsed_time += check_interval
        
        # Check agent registry
        agents = await agent_registry.get_all_agents()
        active_tasks = len(task_scheduler.active_assignments)
        queue_size = len(task_scheduler.task_queue)
        
        # Print status update
        print(f"\n   [{elapsed_time}s] Status Update:")
        print(f"   - Registered agents: {len(agents)}")
        for agent in agents:
            print(f"     • {agent.agent_type}: {agent.status}")
        print(f"   - Active tasks: {active_tasks}, Queued: {queue_size}")
        
        # Check task graph status
        completed_tasks = 0
        failed_tasks = 0
        total_tasks = 0
        
        for proj_id, mgr in task_scheduler.plan_managers.items():
            manager = mgr
            total_tasks = len(manager.graph.tasks)
            for task_id, task in manager.graph.tasks.items():
                if hasattr(task, 'status'):
                    if task.status == 'completed':
                        completed_tasks += 1
                    elif task.status == 'failed':
                        failed_tasks += 1
            
        print(f"   - Task progress: {completed_tasks}/{total_tasks} completed, {failed_tasks} failed")
        
        # Check for files created
        current_files = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.') and not file.endswith('.pyc'):
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    if rel_path not in ['tests/__init__.py', 'src/__init__.py']:
                        current_files.append(rel_path)
        
        if current_files:
            print(f"   - New files created: {', '.join(current_files)}")
        
        # Check for completion or stuck state
        if queue_size == 0 and active_tasks == 0:
            if completed_tasks == total_tasks:
                print("\n   ✓ All tasks completed!")
                break
            elif last_queue_size == 0 and last_active_tasks == 0:
                idle_iterations += 1
                if idle_iterations >= max_idle_iterations:
                    print("\n   ⚠️  System appears idle with incomplete tasks")
                    break
            else:
                idle_iterations = 0
        else:
            idle_iterations = 0
            
        # Check if todo list files were created (success condition)
        todo_files = ['src/todo.py', 'src/storage.py', 'src/__main__.py']
        created_todo_files = [f for f in current_files if any(tf in f for tf in todo_files)]
        
        if len(created_todo_files) >= 3:  # All main files created
            print(f"\n   ✓ Todo list application created successfully!")
            print(f"   Created files: {', '.join(created_todo_files)}")
            break
            
        last_queue_size = queue_size
        last_active_tasks = active_tasks
    
    # Check results
    print("\n8. Checking results...")
    created_files = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if not file.startswith('.') and not file.endswith('.pyc'):
                rel_path = os.path.relpath(os.path.join(root, file), project_path)
                created_files.append(rel_path)
                print(f"   - {rel_path}")
    
    # Stop the scheduler
    await task_scheduler.stop()
    
    # End session
    session_logger.log_event(
        EventType.SESSION_END,
        agent="system",
        data={
            "duration": (datetime.now(timezone.utc) - session_logger.start_time).total_seconds()
        }
    )
    
    # Generate summary
    print("\n" + "=" * 80)
    print("SESSION SUMMARY")
    print("=" * 80)
    summary = session_logger.generate_summary()
    print(summary)
    
    log_file = log_dir / f"session_{session_id}.jsonl"
    print(f"\nFull session log available at:")
    print(f"  {log_file}")
    print(f"\nView with: python -m src.core.simple_session_viewer {log_file}")
    
    # Test summary
    # Check if the main todo list files were created
    todo_files_created = sum(1 for f in created_files if any(tf in f for tf in ['todo.py', 'storage.py', '__main__.py']))
    success = todo_files_created >= 3  # Should have at least the 3 main files
    
    print("\n" + "=" * 80)
    print("Test Summary:")
    print(f"  Success: {success}")
    print(f"  Session ID: {session_id}")
    print(f"  Files Created: {len(created_files)}")
    print(f"  Output: {project_path}")
    print("=" * 80)
    
    return success

async def main():
    """Run the test."""
    try:
        success = await run_todo_list_architect_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())