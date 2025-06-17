#!/usr/bin/env python3
"""
Template for stress test implementation.
Copy this file and modify for each new stress test.
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
        A simple todo list application with GUI that demonstrates:
        - Basic CRUD operations
        - Data persistence with JSON
        - Event handling and UI updates
    """,
    "requirements": [
        "Tkinter-based GUI with modern appearance",
        "Add new todos with text input",
        "Mark todos as complete/incomplete", 
        "Delete todos",
        "Save todos to 'todos.json' automatically",
        "Load todos on startup",
        "Show creation date for each todo",
        "Keyboard shortcuts (Enter to add, Delete key to remove selected)"
    ],
    "success_criteria": [
        "Application launches without errors",
        "Can add at least 5 different todos",
        "Todos persist after closing and reopening app",
        "Can mark todos as complete (visual indication)",
        "Can delete todos",
        "JSON file is created and properly formatted"
    ],
    "expected_structure": {
        "files": [
            "src/__main__.py",  # Entry point
            "src/todo_app.py",  # Main application class
            "todos.json"        # Data file (created at runtime)
        ],
        "dependencies": ["tkinter", "json", "datetime", "os"]
    },
    "task_metadata": {
        "operation": "create",
        "file_operation": "write"
    }
}


async def run_stress_test():
    """Run the stress test and collect metrics."""
    
    # Test configuration
    project_name = TEST_SPEC["name"].lower().replace(" ", "_")
    project_path = Path(f"/home/riley/Programming/agent/test_output/{project_name}")
    
    # Metrics tracking
    metrics = {
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_seconds": 0,
        "models_used": {},
        "tokens_used": 0,
        "retry_count": 0,
        "errors": [],
        "success": False,
        "human_interventions": 0
    }
    
    start_time = time.time()
    
    try:
        # Import required components
        import sys
        sys.path.append('/home/riley/Programming/agent')
        
        from src.architect.architect import Architect
        from src.coding_agent.agent import CodingAgent
        from src.test_agent.test_agent import TestAgent
        from src.proto_gen import messages_pb2
        from src.coding_agent.models import CommitStatus
        
        # Setup project
        print(f"\n{'='*80}")
        print(f"STRESS TEST: {TEST_SPEC['name']}")
        print(f"Phase: {TEST_SPEC['phase']} | Complexity: {TEST_SPEC['complexity']}")
        print(f"{'='*80}\n")
        
        print("1. Setting up project structure...")
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "tests").mkdir(exist_ok=True)
        (project_path / "src" / "__init__.py").touch()
        (project_path / "tests" / "__init__.py").touch()
        
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
        
        # Create coding task
        print("\n3. Creating implementation task...")
        task = messages_pb2.CodingTask()
        task.id = f"task-{project_name}-main"
        task.goal = f"""Create a {TEST_SPEC['name']} with the following requirements:
{chr(10).join(f'        - {req}' for req in TEST_SPEC['requirements'])}
        
        The main entry point should be in src/__main__.py
        """
        
        # Add expected files
        for file_path in TEST_SPEC["expected_structure"]["files"]:
            if file_path.endswith(".py"):
                task.paths.append(file_path)
        
        task.complexity_label = messages_pb2.ComplexityLevel.COMPLEXITY_MODERATE
        
        # Add metadata for file creation
        for key, value in TEST_SPEC.get("task_metadata", {}).items():
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
        
        if result.status == CommitStatus.HARD_FAIL:
            metrics["errors"].append("Implementation failed")
            raise Exception("Implementation failed")
        
        # Verify success criteria
        print("\n5. Verifying success criteria...")
        verification_passed = True
        
        for criterion in TEST_SPEC["success_criteria"]:
            if "launches without errors" in criterion:
                # Try to import the module
                try:
                    import subprocess
                    proc = subprocess.run(
                        [sys.executable, "-m", "src"],
                        cwd=project_path,
                        capture_output=True,
                        timeout=2
                    )
                    if proc.returncode == 0:
                        print(f"  ✓ {criterion}")
                    else:
                        print(f"  ✗ {criterion}: {proc.stderr.decode()}")
                        verification_passed = False
                except Exception as e:
                    print(f"  ✗ {criterion}: {e}")
                    verification_passed = False
            else:
                # For other criteria, we'd need manual verification or specific tests
                print(f"  ? {criterion} (requires manual verification)")
        
        metrics["success"] = verification_passed
        
        # Run tests if requested
        if TEST_SPEC.get("generate_tests", False):
            print("\n6. Generating and running tests...")
            test_agent = TestAgent(
                project_path=str(project_path),
                llm_client=architect.llm_client
            )
            # ... test generation code ...
        
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
        metrics_file = project_path / "test_metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"Test completed in {metrics['duration_seconds']:.2f} seconds")
        print(f"Metrics saved to: {metrics_file}")
        print(f"Success: {metrics['success']}")
        print(f"{'='*80}\n")
    
    return metrics


if __name__ == "__main__":
    # Run the test
    asyncio.run(run_stress_test())