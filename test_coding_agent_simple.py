#!/usr/bin/env python3
"""
Simple test for the Coding Agent focusing on mock functionality.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.coding_agent import CodingAgent, CommitStatus
from src.coding_agent.models import CodeContext, PatchResult, ValidationResult
from src.proto_gen import messages_pb2
from src.core.logging import setup_logging
import logging

# Set up logging
setup_logging(logging.INFO)


class MockRAGClient:
    """Mock RAG client for testing."""
    
    def is_available(self):
        return True
    
    def get_snippet(self, file_path=None, start_line=None, end_line=None, context_lines=None, blob_id=None):
        """Return mock snippet for a file location."""
        content = f"def fetch_data(url):\n    # Mock content for {file_path or 'unknown'}\n    import requests\n    response = requests.get(url)\n    return response.json()"
        return content
    
    def get_blobs(self, blob_ids):
        """Return mock blob contents."""
        return {
            blob_id: f"Mock content for {blob_id}"
            for blob_id in blob_ids
        }
    
    def search(self, query, k=5, filters=None):
        """Return mock search results."""
        return [
            {"file": "main.py", "content": "def example():\n    pass", "score": 0.9},
            {"file": "test.py", "content": "def test_example():\n    assert True", "score": 0.8}
        ]


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def generate(self, prompt, max_tokens=1000, temperature=0.2, system_prompt=""):
        """Generate mock patch."""
        if "error handling" in prompt.lower():
            return """Here's the patch to add error handling:

```diff
--- a/main.py
+++ b/main.py
@@ -1,6 +1,11 @@
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
```"""
        else:
            return "No changes needed."


class MockPatchGenerator:
    """Mock patch generator."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or MockLLMClient()
    
    def generate_patch(self, context, max_tokens=2000, temperature=0.2):
        """Generate mock patch."""
        patch_content = """--- a/main.py
+++ b/main.py
@@ -1,6 +1,11 @@
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
+        return {}"""
        
        return PatchResult(
            success=True,
            patch_content=patch_content,
            files_modified=["main.py"],
            tokens_used=100
        )


class MockValidator:
    """Mock validator."""
    
    def __init__(self, repo_path):
        self.repo_path = repo_path
    
    def validate_patch(self, files_modified, run_tests=True, test_pattern=None):
        """Mock validation - always passes."""
        return ValidationResult(
            syntax_valid=True,
            lint_passed=True,
            tests_passed=True,
            errors=[],
            warnings=["Mock warning: This is a test"]
        )


def test_coding_agent_workflow():
    """Test the basic Coding Agent workflow with mocks."""
    print("\n=== Testing Coding Agent Workflow ===\n")
    
    # Create test task
    task = messages_pb2.CodingTask()
    task.id = "test-task-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    task.goal = "Add error handling to fetch_data function"
    task.paths.append("main.py")
    task.blob_ids.extend(["main.py:1:10:abc123"])
    task.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    task.estimated_tokens = 1000
    
    print(f"📝 Created task: {task.goal}")
    print(f"   Files: {', '.join(task.paths)}")
    print(f"   Blobs: {len(task.blob_ids)}")
    
    # Test context gathering
    print("\n🔍 Testing Context Gathering...")
    from src.coding_agent.context_gatherer import ContextGatherer
    
    rag_client = MockRAGClient()
    gatherer = ContextGatherer("/tmp/test_repo", rag_client)
    
    context = gatherer.gather_context(task, context_tokens=1000)
    print(f"✓ Gathered context:")
    print(f"  - Task goal: {context.task_goal}")
    print(f"  - Blob contents: {len(context.blob_contents)} items")
    print(f"  - File snippets: {len(context.file_snippets)} files")
    print(f"  - Skeleton patches: {len(context.skeleton_patches)} patches")
    
    # Test patch generation
    print("\n🔧 Testing Patch Generation...")
    generator = MockPatchGenerator()
    
    patch_result = generator.generate_patch(context)
    print(f"✓ Generated patch:")
    print(f"  - Success: {patch_result.success}")
    print(f"  - Files modified: {', '.join(patch_result.files_modified)}")
    print(f"  - Tokens used: {patch_result.tokens_used}")
    
    if patch_result.patch_content:
        print("\nPatch preview:")
        lines = patch_result.patch_content.split('\n')[:10]
        for line in lines:
            print(f"  {line}")
        if len(patch_result.patch_content.split('\n')) > 10:
            print("  ...")
    
    # Test validation
    print("\n✅ Testing Validation...")
    validator = MockValidator("/tmp/test_repo")
    
    validation_result = validator.validate_patch(
        patch_result.files_modified,
        run_tests=True
    )
    
    print(f"✓ Validation results:")
    print(f"  - Syntax valid: {validation_result.syntax_valid}")
    print(f"  - Lint passed: {validation_result.lint_passed}")
    print(f"  - Tests passed: {validation_result.tests_passed}")
    print(f"  - Overall valid: {validation_result.is_valid}")
    
    if validation_result.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in validation_result.warnings:
            print(f"  - {warning}")
    
    # Test commit result
    print("\n📦 Creating mock commit result...")
    from src.coding_agent.models import CommitResult
    
    result = CommitResult(
        task_id=task.id,
        status=CommitStatus.SUCCESS,
        commit_sha="abc123def456",
        branch_name="task/test-task-001",
        retries=0,
        llm_tokens_used=100,
        notes=["Successfully added error handling"]
    )
    
    print(f"✓ Commit result:")
    print(f"  - Status: {result.status.name}")
    print(f"  - Commit: {result.commit_sha[:8]}")
    print(f"  - Branch: {result.branch_name}")
    print(f"  - Retries: {result.retries}")
    print(f"  - Tokens used: {result.llm_tokens_used}")
    
    print("\n✅ All workflow components tested successfully!")


def test_rag_integration():
    """Test RAG integration specifically."""
    print("\n\n=== Testing RAG Integration ===\n")
    
    # Test with mock RAG client
    rag_client = MockRAGClient()
    
    print("🔍 Testing RAG availability...")
    print(f"  Available: {rag_client.is_available()}")
    
    print("\n📚 Testing blob fetching...")
    blob_ids = ["file1.py:1:10:abc", "file2.py:20:30:def"]
    blobs = rag_client.get_blobs(blob_ids)
    print(f"  Fetched {len(blobs)} blobs")
    for blob_id, content in blobs.items():
        print(f"  - {blob_id}: {content[:30]}...")
    
    print("\n🔎 Testing semantic search...")
    results = rag_client.search("error handling", k=3)
    print(f"  Found {len(results)} results")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result['file']} (score: {result['score']})")
    
    print("\n✅ RAG integration test completed!")


def test_model_serialization():
    """Test model serialization and protobuf integration."""
    print("\n\n=== Testing Model Serialization ===\n")
    
    # Test CodingTask to internal models
    task = messages_pb2.CodingTask()
    task.id = "serialize-test"
    task.goal = "Test serialization"
    task.paths.append("test.py")
    task.metadata["test_key"] = "test_value"
    
    print("📝 Created protobuf CodingTask:")
    print(f"  ID: {task.id}")
    print(f"  Goal: {task.goal}")
    print(f"  Metadata: {dict(task.metadata)}")
    
    # Test CommitResult to protobuf
    from src.coding_agent.models import CommitResult
    
    result = CommitResult(
        task_id="serialize-test",
        status=CommitStatus.SUCCESS,
        commit_sha="test123",
        branch_name="test/branch",
        retries=1,
        llm_tokens_used=500
    )
    
    print("\n📦 Created CommitResult:")
    print(f"  Task ID: {result.task_id}")
    print(f"  Status: {result.status.name}")
    print(f"  Commit: {result.commit_sha}")
    
    # Test conversion to protobuf
    pb_result = messages_pb2.CommitResult()
    pb_result.task_id = result.task_id
    pb_result.success = (result.status == CommitStatus.SUCCESS)
    pb_result.commit_sha = result.commit_sha
    pb_result.branch_name = result.branch_name
    pb_result.error_message = "" if result.status == CommitStatus.SUCCESS else "Test error"
    # Note: protobuf has different fields than internal model
    
    print("\n✅ Successfully converted to protobuf CommitResult")
    
    print("\n✅ Model serialization test completed!")


if __name__ == "__main__":
    # Check environment
    has_openai = os.getenv("OPENAI_API_KEY") is not None
    
    print("🚀 Coding Agent Simple Test Suite\n")
    print(f"Environment:")
    print(f"  OpenAI API Key: {'✓ Found' if has_openai else '✗ Not found'}")
    print(f"  Python: {sys.version.split()[0]}")
    
    # Run tests
    test_coding_agent_workflow()
    test_rag_integration()
    test_model_serialization()
    
    print("\n\n✅ All tests completed successfully!")