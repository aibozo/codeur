#!/usr/bin/env python3
"""
Test the coding agent with file rewriter integration.
"""

import sys
import os
import asyncio
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


async def test_file_rewriter_integration():
    """Test the Coding Agent with file rewriter fallback."""
    
    # Setup logging
    setup_logging(logging.INFO)
    
    print("\n=== Testing File Rewriter Integration ===\n")
    
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
    
    # RAG Service
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    rag_client = RAGClient(service=rag_service)
    
    # LLM Client
    llm_client = LLMClient()
    print(f"✓ Using model: {llm_client.model}")
    
    # Create Coding Agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client,
        max_retries=3  # Give it enough retries to fallback to file rewriter
    )
    
    # Disable test running in validator for now
    coding_agent.validator.has_pytest = False
    # Also disable linters to see if file rewriter works
    coding_agent.validator.has_black = False
    coding_agent.validator.has_ruff = False
    coding_agent.validator.has_pylint = False
    
    # Create test tasks
    tasks = [
        {
            "id": "test-rewriter-001",
            "goal": "Update the docstring of the get_user method in src/api_client.py to say 'Fetch user data from the API endpoint.'",
            "paths": ["src/api_client.py"],
            "complexity": messages_pb2.COMPLEXITY_TRIVIAL
        },
        {
            "id": "test-rewriter-002", 
            "goal": "Add a docstring to the process method in src/processor.py that says 'Process the input data and return results.'",
            "paths": ["src/processor.py"],
            "complexity": messages_pb2.COMPLEXITY_TRIVIAL
        }
    ]
    
    for task_data in tasks:
        print(f"\n{'='*60}")
        print(f"📝 Testing task: {task_data['id']}")
        print(f"Goal: {task_data['goal']}")
        print('='*60)
        
        # Create task
        task = messages_pb2.CodingTask()
        task.id = task_data["id"]
        task.parent_plan_id = "test-plan-001"
        task.step_number = 1
        task.goal = task_data["goal"]
        for path in task_data["paths"]:
            task.paths.append(path)
        task.complexity_label = task_data["complexity"]
        task.estimated_tokens = 500
        task.base_commit_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        # Process the task
        print("\n💻 Processing task...")
        
        try:
            result = coding_agent.process_task(task)
            
            print(f"\n📊 Result:")
            print(f"  Status: {result.status.name}")
            print(f"  Retries: {result.retries}")
            print(f"  Tokens used: {result.llm_tokens_used}")
            
            if result.notes:
                print("\n📝 Notes:")
                for note in result.notes:
                    print(f"  - {note}")
            
            if result.status.name == "SUCCESS":
                print(f"\n✅ Success!")
                print(f"  Commit: {result.commit_sha[:8] if result.commit_sha else 'N/A'}")
                print(f"  Branch: {result.branch_name}")
                
                # Show the diff
                diff = subprocess.run(
                    ["git", "show", result.commit_sha],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if diff.returncode == 0:
                    print("\n📄 Generated change:")
                    print(diff.stdout)
            else:
                print(f"\n❌ Failed: {result.status.name}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✨ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_file_rewriter_integration())