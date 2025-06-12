#!/usr/bin/env python3
"""
Test the coding agent with GPT-4 for better diff generation.
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set model to GPT-4 for better diff handling
os.environ["GENERAL_MODEL"] = "gpt-4-turbo-preview"  # or "gpt-4" if you prefer

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.coding_agent.patch_generator_v2 import ImprovedPatchGenerator
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging
import logging


async def test_improved_patch_generation():
    """Test with improved patch generation."""
    
    # Setup logging
    setup_logging(logging.INFO)
    
    print("\n=== Testing Improved Patch Generation ===\n")
    
    # Repository path
    repo_path = Path(__file__).parent / "test_repo"
    
    # Clean up any existing branches
    import subprocess
    try:
        # Go to master branch
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
        # Delete test branches
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
    
    # LLM Client with GPT-4
    llm_client = LLMClient(model="gpt-4-turbo-preview")
    print(f"✓ Using model: {llm_client.model}")
    
    # Create Coding Agent with improved patch generator
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client
    )
    
    # Replace the patch generator with improved version
    coding_agent.patch_generator = ImprovedPatchGenerator(llm_client)
    
    # Create a simple test task
    print("\n📝 Creating test task...")
    
    task = messages_pb2.CodingTask()
    task.id = "test-task-001"
    task.parent_plan_id = "test-plan-001"
    task.step_number = 1
    task.goal = "Add a docstring to the get_user method in src/api_client.py that says 'Fetch user data from the API endpoint.'"
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
    
    # Process the task
    print("\n💻 Processing task...")
    
    try:
        result = coding_agent.process_task(task)
        
        print(f"\n📊 Result:")
        print(f"  Status: {result.status.name}")
        
        if result.status.name == "SUCCESS":
            print(f"  ✅ Success!")
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
            print(f"  ❌ Failed: {result.status.name}")
            for note in result.notes:
                print(f"  - {note}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Test complete!")


async def test_with_different_models():
    """Test with different models to find the best one for diffs."""
    models = ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"]
    
    for model in models:
        print(f"\n\n=== Testing with {model} ===")
        os.environ["GENERAL_MODEL"] = model
        
        # Quick test of patch generation
        from src.llm import LLMClient
        from src.coding_agent.patch_generator_v2 import ImprovedPatchGenerator
        
        try:
            llm = LLMClient(model=model)
            generator = ImprovedPatchGenerator(llm)
            
            # Create mock context
            from src.coding_agent.models import CodeContext
            context = CodeContext(
                task_goal="Add a comment saying 'Hello World' at the top of the function",
                file_snippets={
                    "test.py": """def example():
    return 42"""
                }
            )
            
            result = generator.generate_patch(context)
            if result.success:
                print(f"✓ {model} generated valid patch")
                print("Patch preview:")
                print(result.patch_content[:200] + "..." if len(result.patch_content) > 200 else result.patch_content)
            else:
                print(f"✗ {model} failed: {result.error_message}")
                
        except Exception as e:
            print(f"✗ {model} error: {e}")


if __name__ == "__main__":
    # Test improved generation
    asyncio.run(test_improved_patch_generation())
    
    # Optionally test different models
    # asyncio.run(test_with_different_models())