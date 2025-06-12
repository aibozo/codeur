#!/usr/bin/env python3
"""
Test the coding agent with o3 model and proper line numbers.
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables with o3 model
load_dotenv()
os.environ["GENERAL_MODEL"] = "o3-mini"  # Use o3 for code generation

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging
import logging


async def test_o3_with_line_numbers():
    """Test the Coding Agent with o3 model and line numbers in context."""
    
    # Setup logging
    setup_logging(logging.INFO)
    
    print("\n=== Testing with o3 Model and Line Numbers ===\n")
    
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
    
    # LLM Client with o3
    llm_client = LLMClient(model="o3-mini")
    print(f"✓ Using model: {llm_client.model}")
    
    # Create Coding Agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client,
        max_retries=2  # Less retries needed with better model
    )
    
    # Test task
    print("\n📝 Creating test task...")
    
    task = messages_pb2.CodingTask()
    task.id = "test-o3-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    task.goal = "Update the docstring of the get_user method in src/api_client.py to say 'Fetch user data from the API endpoint.'"
    task.paths.append("src/api_client.py")
    task.complexity_label = messages_pb2.COMPLEXITY_TRIVIAL
    task.estimated_tokens = 500
    task.base_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    print(f"Task: {task.goal}")
    print(f"File: {task.paths[0]}")
    print(f"Model: {llm_client.model}")
    
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
            
            # Debug: Show what context was provided
            print("\n🔍 Debug - Context provided to LLM:")
            from src.coding_agent.context_gatherer import ContextGatherer
            gatherer = ContextGatherer(str(repo_path), rag_client)
            context = gatherer.gather_context(task)
            
            print("\nFile snippets format:")
            for path, content in context.file_snippets.items():
                print(f"\n--- {path} ---")
                lines = content.split('\n')[:10]
                for line in lines:
                    print(line)
                print("...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_o3_with_line_numbers())