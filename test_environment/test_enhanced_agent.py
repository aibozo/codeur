#!/usr/bin/env python3
"""
Test the enhanced coding agent with tool support.
"""

import sys
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging
import logging


def test_enhanced_agent():
    """Test the enhanced coding agent with a real task."""
    
    # Setup logging
    setup_logging(logging.INFO)
    
    print("\n=== Testing Enhanced Coding Agent ===\n")
    
    # Repository path
    repo_path = Path(__file__).parent / "test_repo"
    
    # Clean up any existing branches
    try:
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
        branches = subprocess.run(["git", "branch"], cwd=repo_path, capture_output=True, text=True)
        for line in branches.stdout.split('\n'):
            if 'coding/' in line:
                branch = line.strip().replace('* ', '')
                subprocess.run(["git", "branch", "-D", branch], cwd=repo_path, capture_output=True)
    except:
        pass
    
    # Initialize components
    print("🔧 Initializing components...")
    
    # RAG Service - index the repository first
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Index all Python files
    print("📚 Indexing repository...")
    python_files = list(repo_path.glob("**/*.py"))
    for py_file in python_files:
        if ".rag" not in str(py_file):
            print(f"  Indexing {py_file.relative_to(repo_path)}")
            rag_service.index_file(str(py_file))
    
    rag_client = RAGClient(service=rag_service)
    
    # LLM Client with o3
    llm_client = LLMClient(model="o3")
    print(f"✓ Using model: {llm_client.model}")
    
    # Create Coding Agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client,
        max_retries=3
    )
    
    # Create a real task
    print("\n📝 Creating test task...")
    
    task = messages_pb2.CodingTask()
    task.id = "test-enhanced-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    
    # A real task that requires understanding the code
    task.goal = "Add error handling to the get_user method in src/api_client.py. It should catch requests.exceptions.RequestException and return None with a log message when the request fails."
    task.paths.append("src/api_client.py")
    task.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    task.estimated_tokens = 1000
    task.base_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    print(f"Task: {task.goal}")
    print(f"Target file: {task.paths[0]}")
    print(f"Complexity: {task.complexity_label}")
    
    # Process the task
    print("\n💻 Processing task...")
    print("(The agent should use tools to read files and understand the context)\n")
    
    try:
        result = coding_agent.process_task(task)
        
        print(f"\n📊 Result:")
        print(f"  Status: {result.status.name}")
        print(f"  Retries: {result.retries}")
        print(f"  Tokens used: {result.llm_tokens_used}")
        
        if result.notes:
            print("\n📝 Process notes:")
            for note in result.notes:
                print(f"  - {note}")
        
        if result.status.name == "SUCCESS":
            print(f"\n✅ Success!")
            print(f"  Commit: {result.commit_sha[:8] if result.commit_sha else 'N/A'}")
            print(f"  Branch: {result.branch_name}")
            
            # Show the diff
            diff = subprocess.run(
                ["git", "show", "--no-patch", "--format=fuller", result.commit_sha],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            print("\n📄 Commit details:")
            print(diff.stdout)
            
            # Show the actual changes
            diff = subprocess.run(
                ["git", "show", result.commit_sha],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            print("\n📄 Generated changes:")
            print(diff.stdout)
            
            # Verify the changes make sense
            print("\n🔍 Verification:")
            api_file = repo_path / "src/api_client.py"
            content = api_file.read_text()
            
            checks = [
                ("imports logging", "import logging" in content),
                ("imports requests.exceptions", "requests.exceptions" in content or "from requests import exceptions" in content),
                ("has try/except", "try:" in content and "except" in content),
                ("returns None on error", "return None" in content),
                ("has log message", "log" in content.lower())
            ]
            
            for check_name, check_result in checks:
                print(f"  ✓ {check_name}: {'Yes' if check_result else 'No'}")
            
        else:
            print(f"\n❌ Failed: {result.status.name}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Test complete!")


if __name__ == "__main__":
    test_enhanced_agent()