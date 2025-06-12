#!/usr/bin/env python3
"""
Test with files that actually exist in the test repo.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.models import CodeContext
from src.coding_agent.context_gatherer import ContextGatherer
from src.proto_gen import messages_pb2
from src.llm import LLMClient
from src.coding_agent import CodingAgent
from src.rag_service import RAGClient, RAGService
import subprocess


def test_context_with_actual_file():
    """Test context gathering with a file that exists."""
    
    print("\n=== Testing Context with Actual Files ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    context_gatherer = ContextGatherer(str(repo_path))
    
    # Create task for a file that exists
    task = messages_pb2.CodingTask()
    task.goal = "Add error handling to the get_user method"
    task.paths.append("src/api_client.py")
    
    print("📝 Task:", task.goal)
    print("📁 File:", task.paths[0])
    
    # Check file exists
    file_path = repo_path / task.paths[0]
    print(f"\n✅ File exists: {file_path.exists()}")
    
    # Gather context
    print("\n1️⃣ Gathering context...")
    context = context_gatherer.gather_context(task)
    
    print(f"\n📊 Context stats:")
    print(f"  - File snippets: {len(context.file_snippets)}")
    print(f"  - Token count: {context.token_count}")
    
    # Check if we have the file content
    if "src/api_client.py" in context.file_snippets:
        snippet = context.file_snippets["src/api_client.py"]
        lines = snippet.split('\n')
        
        print(f"\n📄 File snippet analysis:")
        print(f"  - Total lines: {len(lines)}")
        
        # Check for line numbers
        has_line_numbers = False
        for line in lines[:5]:
            print(f"  Preview: {line}")
            if line.strip() and ':' in line:
                # Check if starts with number
                parts = line.split(':', 1)
                if parts[0].strip().isdigit():
                    has_line_numbers = True
        
        print(f"\n✅ Has line numbers: {has_line_numbers}")
    else:
        print("\n❌ File not in context!")


def test_full_agent_simple():
    """Test the full agent with a simple task."""
    
    print("\n\n=== Testing Full Agent (Simple) ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Initialize components
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Quick index
    api_file = repo_path / "src/api_client.py"
    if api_file.exists():
        rag_service.index_file(str(api_file))
    
    rag_client = RAGClient(service=rag_service)
    
    # Use fast model
    llm_client = LLMClient(model="gpt-4o")
    
    # Create agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client,
        max_retries=1
    )
    
    # Create simple task
    task = messages_pb2.CodingTask()
    task.id = "test-simple-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    task.goal = "Add a comment to the APIClient class explaining what it does"
    task.paths.append("src/api_client.py")
    task.complexity_label = 1  # SIMPLE
    task.estimated_tokens = 500
    task.base_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    print(f"📝 Task: {task.goal}")
    print(f"📁 File: {task.paths[0]}")
    
    # Clean up branches
    subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
    
    # Process task
    print("\n💻 Processing...")
    
    try:
        result = coding_agent.process_task(task)
        
        print(f"\n📊 Result: {result.status.name}")
        print(f"  Retries: {result.retries}")
        print(f"  Tokens: {result.llm_tokens_used}")
        
        # Show key notes
        if result.notes:
            print("\n📝 Key notes:")
            for note in result.notes[-3:]:
                print(f"  - {note}")
        
        if result.status.name == "SUCCESS":
            print(f"\n✅ Success! Commit: {result.commit_sha[:8]}")
            
            # Show what changed
            diff = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD", "--", "src/api_client.py"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            print("\n📄 Changes made:")
            print(diff.stdout[:500] + "..." if len(diff.stdout) > 500 else diff.stdout)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_context_with_actual_file()
    test_full_agent_simple()