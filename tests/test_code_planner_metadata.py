#!/usr/bin/env python3
"""
Test Code Planner metadata functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner import CodePlanner
from src.proto_gen import messages_pb2
from google.protobuf import json_format


def test_metadata():
    """Test that metadata is properly populated in CodingTasks."""
    print("🧪 Testing Code Planner Metadata")
    print("=" * 50)
    
    # Create test repository
    test_repo = Path("test_metadata_repo")
    test_repo.mkdir(exist_ok=True)
    
    # Create test file
    src_dir = test_repo / "src"
    src_dir.mkdir(exist_ok=True)
    
    test_file = src_dir / "calculator.py"
    test_file.write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    result = 0
    for _ in range(b):
        result = add(result, a)
    return result

class Calculator:
    def __init__(self):
        self.memory = 0
    
    def calculate(self, operation, a, b):
        if operation == "add":
            return add(a, b)
        elif operation == "multiply":
            return multiply(a, b)
""")
    
    # Create test plan
    plan = messages_pb2.Plan()
    plan.id = "metadata-test-plan"
    plan.parent_request_id = "request-123"
    
    # Refactor step
    step1 = plan.steps.add()
    step1.order = 1
    step1.goal = "Refactor the multiply function to be more efficient"
    step1.kind = messages_pb2.STEP_KIND_REFACTOR
    step1.hints.append("Use built-in multiplication operator")
    
    # Test step
    step2 = plan.steps.add()
    step2.order = 2
    step2.goal = "Add unit tests for Calculator class"
    step2.kind = messages_pb2.STEP_KIND_TEST
    step2.hints.append("Test all methods")
    
    plan.affected_paths.extend(["src/calculator.py"])
    # Also add hints that mention the file
    step1.hints.append("in src/calculator.py")
    step2.hints.append("for src/calculator.py")
    
    # Process plan
    planner = CodePlanner(str(test_repo))
    task_bundle = planner.process_plan(plan)
    
    print(f"✓ Generated TaskBundle: {task_bundle.id}")
    print(f"  Tasks: {len(task_bundle.tasks)}")
    
    # Check metadata
    for i, task in enumerate(task_bundle.tasks, 1):
        print(f"\n📋 Task {i} Metadata:")
        print(f"  ID: {task.id}")
        print(f"  Goal: {task.goal}")
        
        # Print all metadata
        for key, value in task.metadata.items():
            print(f"  Metadata[{key}]: {value}")
        
        # Verify expected metadata
        assert "step_kind" in task.metadata, f"Missing step_kind in task {i}"
        assert "affected_symbols" in task.metadata, f"Missing affected_symbols in task {i}"
        
        if i == 1:
            assert task.metadata["step_kind"] == "REFACTOR", f"Wrong step_kind for task 1"
            # Check if we found any symbols (multiply function should be in the goal)
            print(f"  Files analyzed: {task.paths}")
            if task.metadata["affected_symbols"]:
                print(f"  Found symbols: {task.metadata['affected_symbols']}")
        elif i == 2:
            assert task.metadata["step_kind"] == "TEST", f"Wrong step_kind for task 2"
    
    # Also check JSON serialization works
    print("\n📄 JSON Serialization Test:")
    task_dict = json_format.MessageToDict(task_bundle.tasks[0])
    print(f"  Metadata in JSON: {task_dict.get('metadata', {})}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_repo, ignore_errors=True)
    
    print("\n✅ Metadata test passed!")
    return True


if __name__ == "__main__":
    success = test_metadata()
    sys.exit(0 if success else 1)