#!/usr/bin/env python3
"""
Stress Test: Todo List Application
Tests multi-file organization and data persistence.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

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
    "requirements": [
        "Create a GUI todo list application using tkinter",
        "Main window should have a title 'Todo List'",
        "Text input field at top for entering new todos",
        "Add button next to input field (or press Enter to add)",
        "Scrollable list showing all todos below input area",
        "Each todo item should show: checkbox, todo text, creation date",
        "Clicking checkbox marks todo as complete (strikethrough text)",
        "Delete button or right-click menu to remove todos",
        "All todos saved to 'todos.json' file automatically",
        "Load existing todos from file on startup",
        "Clean modern UI with proper spacing and colors",
        "Window should be resizable with proper layout adjustment",
        "Clear completed button to remove all completed todos",
        "Show count of active todos at bottom"
    ],
    "success_criteria": [
        "Application launches without errors",
        "Can add new todos by typing and pressing Enter or clicking Add",
        "Todos appear in the list with creation timestamp",
        "Can mark todos as complete/incomplete by clicking checkbox",
        "Completed todos show visual distinction (strikethrough)",
        "Can delete individual todos",
        "Todos persist in todos.json file",
        "Todos reload correctly after restarting app",
        "UI is responsive and properly laid out"
    ],
    "expected_structure": {
        "files": [
            "src/__main__.py",      # Entry point
            "src/todo_app.py",      # Main application window
            "src/todo_model.py",    # Todo data model and storage
            "src/todo_item.py"      # Todo item widget
        ],
        "dependencies": ["tkinter", "json", "datetime", "os", "pathlib"]
    },
    "task_metadata": {
        "operation": "create",
        "file_operation": "write"
    }
}


async def run_todo_list_test():
    """Run the todo list stress test."""
    
    # Test configuration
    project_name = "todo_list_app"
    project_path = Path(f"/home/riley/Programming/agent/test_output/{project_name}")
    
    # Metrics tracking
    metrics = {
        "test_name": TEST_SPEC["name"],
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_seconds": 0,
        "models_used": {},
        "tokens_used": 0,
        "retry_count": 0,
        "errors": [],
        "success": False,
        "files_created": [],
        "verification_results": {}
    }
    
    start_time = time.time()
    
    try:
        # Import required components
        import sys
        sys.path.append('/home/riley/Programming/agent')
        
        from src.architect.architect import Architect
        from src.coding_agent.agent import CodingAgent
        from src.proto_gen import messages_pb2
        from src.coding_agent.models import CommitStatus
        from src.git_operations import GitOperations
        
        # Setup project
        print(f"\n{'='*80}")
        print(f"STRESS TEST: {TEST_SPEC['name']}")
        print(f"Phase: {TEST_SPEC['phase']} | Complexity: {TEST_SPEC['complexity']}")
        print(f"{'='*80}\n")
        
        # Clean up any previous test
        if project_path.exists():
            import shutil
            shutil.rmtree(project_path)
        
        print("1. Setting up project structure...")
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "tests").mkdir(exist_ok=True)
        (project_path / "src" / "__init__.py").touch()
        (project_path / "tests" / "__init__.py").touch()
        
        # Initialize git
        git_ops = GitOperations(str(project_path))
        git_ops.init_repo()
        git_ops.commit_changes("Initial commit", allow_empty=True)
        
        # Initialize agents
        print("\n2. Initializing agents...")
        architect = Architect(
            project_path=str(project_path),
            use_llm=True
        )
        metrics["models_used"]["architect"] = architect.llm_client.model_card.display_name
        
        coding_agent = CodingAgent(
            repo_path=str(project_path),
            llm_client=architect.llm_client,
            use_smart_context=True
        )
        metrics["models_used"]["coder"] = coding_agent.llm_client.model_card.display_name
        
        # Create detailed implementation task
        print("\n3. Creating implementation task...")
        task = messages_pb2.CodingTask()
        task.id = "task-todo-app-implementation"
        task.goal = f"""Create a Todo List GUI application with the following structure and requirements:

{chr(10).join(f'        {req}' for req in TEST_SPEC['requirements'])}

        File Structure:
        - src/__main__.py: Entry point that creates and runs the app
        - src/todo_app.py: Main TodoApp class with the GUI window
        - src/todo_model.py: TodoModel class for data management and JSON persistence  
        - src/todo_item.py: TodoItem widget class for individual todo display

        Implementation notes:
        - Use proper separation of concerns (MVC pattern)
        - TodoModel handles all data operations and file I/O
        - TodoApp manages the main window and coordinates components
        - TodoItem is a custom widget for each todo in the list
        - Ensure proper error handling for file operations
        """
        
        # Add all expected Python files
        task.paths.extend([
            "src/__main__.py",
            "src/todo_app.py", 
            "src/todo_model.py",
            "src/todo_item.py"
        ])
        
        task.complexity_label = messages_pb2.ComplexityLevel.COMPLEXITY_MODERATE
        
        # Add metadata for file creation
        for key, value in TEST_SPEC["task_metadata"].items():
            task.metadata[key] = value
        
        # Execute coding task
        print("\n4. Executing implementation...")
        result = await coding_agent.process_task(task)
        
        metrics["retry_count"] = result.retries
        metrics["tokens_used"] = result.llm_tokens_used
        
        print(f"\nImplementation Status: {result.status.name}")
        if result.notes:
            for note in result.notes:
                print(f"  - {note}")
                if "Created empty file:" in note or "Rewrote file:" in note:
                    metrics["files_created"].append(note.split(": ")[1])
        
        if result.status == CommitStatus.HARD_FAIL:
            metrics["errors"].append("Implementation failed")
            raise Exception("Implementation failed - check logs for details")
        
        # Verify file creation
        print("\n5. Verifying file structure...")
        for expected_file in TEST_SPEC["expected_structure"]["files"]:
            if expected_file.endswith(".json"):
                continue  # Skip runtime files
            file_path = project_path / expected_file
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  ✓ {expected_file} ({size} bytes)")
                metrics["verification_results"][expected_file] = {"exists": True, "size": size}
            else:
                print(f"  ✗ {expected_file} (missing)")
                metrics["verification_results"][expected_file] = {"exists": False}
        
        # Try to run the application
        print("\n6. Testing application launch...")
        try:
            import subprocess
            # Test import first
            proc = subprocess.run(
                [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from src import __main__"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if proc.returncode == 0:
                print("  ✓ Application modules import successfully")
                metrics["verification_results"]["imports"] = True
            else:
                print(f"  ✗ Import failed: {proc.stderr}")
                metrics["verification_results"]["imports"] = False
                metrics["errors"].append(f"Import error: {proc.stderr}")
        
        except Exception as e:
            print(f"  ✗ Launch test failed: {e}")
            metrics["errors"].append(f"Launch test error: {str(e)}")
        
        # Check code quality
        print("\n7. Code quality checks...")
        for py_file in project_path.glob("src/*.py"):
            if py_file.name == "__init__.py":
                continue
            content = py_file.read_text()
            
            # Basic quality checks
            has_class = "class " in content
            has_functions = "def " in content
            has_docstrings = '"""' in content or "'''" in content
            proper_imports = "import " in content or "from " in content
            
            print(f"\n  {py_file.name}:")
            print(f"    - Has classes: {'✓' if has_class else '✗'}")
            print(f"    - Has functions: {'✓' if has_functions else '✗'}")
            print(f"    - Has docstrings: {'✓' if has_docstrings else '✗'}")
            print(f"    - Has imports: {'✓' if proper_imports else '✗'}")
        
        # Determine overall success
        required_files_exist = all(
            metrics["verification_results"].get(f, {}).get("exists", False)
            for f in TEST_SPEC["expected_structure"]["files"]
            if f.endswith(".py")
        )
        
        metrics["success"] = (
            result.status != CommitStatus.HARD_FAIL and
            required_files_exist and
            len(metrics["errors"]) == 0
        )
        
    except Exception as e:
        metrics["errors"].append(str(e))
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        end_time = time.time()
        metrics["end_time"] = datetime.now().isoformat()
        metrics["duration_seconds"] = end_time - start_time
        
        # Save metrics
        if project_path.exists():
            metrics_file = project_path / "test_metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"Test Summary:")
        print(f"  Duration: {metrics['duration_seconds']:.2f} seconds")
        print(f"  Success: {metrics['success']}")
        print(f"  Models: {', '.join(metrics['models_used'].values())}")
        print(f"  Tokens Used: {metrics['tokens_used']:,}")
        print(f"  Files Created: {len(metrics['files_created'])}")
        print(f"  Errors: {len(metrics['errors'])}")
        if project_path.exists():
            print(f"  Output: {project_path}")
        print(f"{'='*80}\n")
    
    return metrics


if __name__ == "__main__":
    # Load environment variables
    import sys
    sys.path.append('/home/riley/Programming/agent')
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the test
    asyncio.run(run_todo_list_test())