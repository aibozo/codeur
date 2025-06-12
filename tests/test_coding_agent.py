#!/usr/bin/env python3
"""
Test the Coding Agent with RAG integration.
"""

import sys
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent, CommitStatus
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging
import logging

# Set up logging
setup_logging(logging.INFO)


def create_test_repository():
    """Create a test git repository with some code."""
    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix="coding_agent_test_")
    test_path = Path(test_dir)
    
    # Initialize git repo
    os.system(f"cd {test_path} && git init")
    os.system(f"cd {test_path} && git config user.email 'test@example.com'")
    os.system(f"cd {test_path} && git config user.name 'Test User'")
    
    # Create some test files
    (test_path / "main.py").write_text('''
def fetch_data(url):
    """Fetch data from URL."""
    import requests
    response = requests.get(url)
    return response.json()

def process_data(data):
    """Process the fetched data."""
    results = []
    for item in data:
        if item.get("active"):
            results.append(item["name"])
    return results

if __name__ == "__main__":
    data = fetch_data("https://api.example.com/data")
    results = process_data(data)
    print(results)
''')
    
    (test_path / "test_main.py").write_text('''
import pytest
from main import fetch_data, process_data

def test_process_data():
    """Test data processing."""
    data = [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
        {"name": "Charlie", "active": True}
    ]
    
    results = process_data(data)
    assert results == ["Alice", "Charlie"]

@pytest.mark.fast
def test_process_empty_data():
    """Test processing empty data."""
    assert process_data([]) == []
''')
    
    (test_path / "requirements.txt").write_text("requests\npytest\n")
    
    # Create initial commit
    os.system(f"cd {test_path} && git add .")
    os.system(f"cd {test_path} && git commit -m 'Initial commit'")
    
    return test_path


def create_test_task(task_type="error_handling"):
    """Create a test CodingTask."""
    task = messages_pb2.CodingTask()
    task.id = "test-task-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    
    if task_type == "error_handling":
        task.goal = "Add error handling to fetch_data function for network errors"
        task.paths.append("main.py")
        task.skeleton_patch.append("""
--- a/main.py
+++ b/main.py
@@ ... @@
 def fetch_data(url):
     # TODO: Add try-except for requests.exceptions
     # TODO: Return None or empty dict on error
     # TODO: Log the error
""")
    elif task_type == "new_function":
        task.goal = "Add a new function to validate URLs before fetching"
        task.paths.append("main.py")
        task.skeleton_patch.append("""
--- a/main.py
+++ b/main.py
@@ ... @@
+def validate_url(url):
+    # TODO: Check if URL is valid
+    # TODO: Return True if valid, False otherwise
""")
    elif task_type == "test_update":
        task.goal = "Add test for error handling in fetch_data"
        task.paths.append("test_main.py")
    
    task.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    task.estimated_tokens = 1000
    
    return task


def test_coding_agent_basic():
    """Test basic Coding Agent functionality."""
    print("\n=== Testing Basic Coding Agent ===\n")
    
    # Create test repository
    test_repo = create_test_repository()
    print(f"✓ Created test repository at {test_repo}")
    
    try:
        # Create Coding Agent (without RAG for basic test)
        agent = CodingAgent(
            repo_path=str(test_repo),
            rag_client=None,
            llm_client=None,  # Will try to create one
            max_retries=1
        )
        
        # Create a test task
        task = create_test_task("error_handling")
        
        # Process the task
        print(f"\n📝 Processing task: {task.goal}")
        result = agent.process_task(task)
        
        # Check results
        print(f"\n📊 Results:")
        print(f"  Status: {result.status.value}")
        print(f"  Task ID: {result.task_id}")
        print(f"  Branch: {result.branch_name}")
        print(f"  Commit: {result.commit_sha}")
        print(f"  Retries: {result.retries}")
        print(f"  Tokens used: {result.llm_tokens_used}")
        
        if result.notes:
            print(f"\n📋 Notes:")
            for note in result.notes:
                print(f"  - {note}")
        
        # Check if commit was created
        if result.status == CommitStatus.SUCCESS:
            print(f"\n✅ Successfully created commit!")
            
            # Show the diff
            os.system(f"cd {test_repo} && git show --stat {result.commit_sha}")
        else:
            print(f"\n❌ Task failed with status: {result.status.value}")
    
    finally:
        # Cleanup
        shutil.rmtree(test_repo, ignore_errors=True)


def test_coding_agent_with_rag():
    """Test Coding Agent with RAG integration."""
    print("\n\n=== Testing Coding Agent with RAG ===\n")
    
    # Create test repository
    test_repo = create_test_repository()
    print(f"✓ Created test repository at {test_repo}")
    
    try:
        # Initialize RAG service
        print("\n🔍 Initializing RAG service...")
        rag_dir = test_repo / ".rag"
        rag_service = RAGService(
            persist_directory=str(rag_dir), repo_path=str(test_repo)
        )
        rag_client = RAGClient(service=rag_service)
        
        if rag_client.is_available():
            print("✓ RAG service available")
            
            # Index the repository
            print("📚 Indexing repository...")
            results = rag_client.index_directory(
                directory=str(test_repo),
                extensions=[".py"]
            )
            print(f"✓ Indexed {len(results)} files")
        else:
            print("⚠ RAG service not available (no OpenAI key?)")
            rag_client = None
        
        # Create LLM client
        llm_client = None
        if os.getenv("OPENAI_API_KEY"):
            llm_client = LLMClient()
            print("✓ LLM client initialized")
        else:
            print("⚠ No OpenAI API key - will use mock responses")
        
        # Create Coding Agent with RAG
        agent = CodingAgent(
            repo_path=str(test_repo),
            rag_client=rag_client,
            llm_client=llm_client,
            max_retries=2
        )
        
        # Test different task types
        task_types = ["error_handling", "new_function"]
        
        for task_type in task_types:
            print(f"\n📝 Testing task type: {task_type}")
            
            # Create task
            task = create_test_task(task_type)
            task.id = f"test-task-{task_type}"
            
            # Add some blob IDs if RAG is available
            if rag_client:
                task.blob_ids.extend([
                    "main.py:1:10:abc123",
                    "test_main.py:5:15:def456"
                ])
            
            # Process task
            result = agent.process_task(task)
            
            # Show results
            print(f"  Status: {result.status.value}")
            if result.commit_sha:
                print(f"  Commit: {result.commit_sha[:8]}")
            
            # Reset to main branch for next test
            os.system(f"cd {test_repo} && git checkout main 2>/dev/null")
    
    finally:
        # Cleanup
        shutil.rmtree(test_repo, ignore_errors=True)


def test_validation_flow():
    """Test the validation flow specifically."""
    print("\n\n=== Testing Validation Flow ===\n")
    
    # Create test repository
    test_repo = create_test_repository()
    
    try:
        from src.coding_agent import GitOperations, PatchValidator
        
        # Test git operations
        print("🔧 Testing Git Operations...")
        git_ops = GitOperations(str(test_repo))
        
        current_branch = git_ops.get_current_branch()
        print(f"  Current branch: {current_branch}")
        
        current_commit = git_ops.get_current_commit()
        print(f"  Current commit: {current_commit[:8]}")
        
        # Create a test branch
        branch_created = git_ops.create_branch("test/validation-flow")
        print(f"  Branch created: {branch_created}")
        
        # Test patch application
        print("\n🩹 Testing Patch Application...")
        test_patch = """--- a/main.py
+++ b/main.py
@@ -1,7 +1,12 @@
 def fetch_data(url):
     \"\"\"Fetch data from URL.\"\"\"
     import requests
-    response = requests.get(url)
-    return response.json()
+    try:
+        response = requests.get(url, timeout=10)
+        response.raise_for_status()
+        return response.json()
+    except requests.exceptions.RequestException as e:
+        print(f"Error fetching data: {e}")
+        return {}
 
 def process_data(data):"""
        
        applied, error = git_ops.apply_patch(test_patch)
        print(f"  Patch applied: {applied}")
        if error:
            print(f"  Error: {error}")
        
        # Test validation
        print("\n✅ Testing Validation...")
        validator = PatchValidator(str(test_repo))
        
        validation_result = validator.validate_patch(
            ["main.py"],
            run_tests=True,
            test_pattern="fast"
        )
        
        print(f"  Syntax valid: {validation_result.syntax_valid}")
        print(f"  Lint passed: {validation_result.lint_passed}")
        print(f"  Tests passed: {validation_result.tests_passed}")
        print(f"  Overall valid: {validation_result.is_valid}")
        
        if validation_result.errors:
            print(f"\n  Errors:")
            for error in validation_result.errors:
                print(f"    - {error}")
        
        if validation_result.warnings:
            print(f"\n  Warnings:")
            for warning in validation_result.warnings:
                print(f"    - {warning}")
    
    finally:
        # Cleanup
        shutil.rmtree(test_repo, ignore_errors=True)


if __name__ == "__main__":
    # Check environment
    has_openai = os.getenv("OPENAI_API_KEY") is not None
    
    print("🚀 Coding Agent Test Suite\n")
    print(f"Environment:")
    print(f"  OpenAI API Key: {'✓ Found' if has_openai else '✗ Not found'}")
    print(f"  Python: {sys.version.split()[0]}")
    
    if not has_openai:
        print("\n⚠️  Note: Without OpenAI API key, patch generation will fail.")
        print("  The test will demonstrate the agent workflow and validation.")
    
    # Run tests
    test_validation_flow()
    test_coding_agent_basic()
    test_coding_agent_with_rag()
    
    print("\n✅ All tests completed!")