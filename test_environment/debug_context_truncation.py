#!/usr/bin/env python3
"""
Debug how much context is actually provided to o3.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.context_gatherer import ContextGatherer
from src.coding_agent.models import CodeContext
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService


def debug_context_truncation():
    """See exactly what context o3 receives."""
    
    print("=== Debugging Context Truncation ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Create a test task
    task = messages_pb2.CodingTask()
    task.id = "debug-001"
    task.goal = "Update the docstring of get_user method"
    task.paths.append("src/api_client.py")
    
    # Initialize gatherer
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    rag_client = RAGClient(service=rag_service)
    
    gatherer = ContextGatherer(str(repo_path), rag_client)
    
    # Gather context
    context = gatherer.gather_context(task)
    
    # Check file content
    print("1. FILE CONTENT IN CONTEXT:")
    for path, content in context.file_snippets.items():
        print(f"\nFile: {path}")
        print(f"Total length: {len(content)} characters")
        print(f"Total lines: {len(content.splitlines())}")
        print("\nFirst 10 lines:")
        for i, line in enumerate(content.splitlines()[:10], 1):
            print(f"  {line}")
    
    # Check what gets sent to prompt
    print("\n\n2. CONTEXT SENT TO PROMPT (via to_prompt_context):")
    prompt_context = context.to_prompt_context(max_tokens=3000)
    print(prompt_context)
    
    # Check actual file
    print("\n\n3. ACTUAL FILE CONTENT:")
    api_file = repo_path / "src/api_client.py"
    if api_file.exists():
        content = api_file.read_text()
        print(f"Total file size: {len(content)} characters")
        print(f"Total lines: {len(content.splitlines())}")
        
        # Find get_user method
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "def get_user" in line:
                print(f"\nget_user method starts at line {i+1}")
                # Show context around it
                start = max(0, i-3)
                end = min(len(lines), i+10)
                print("\nContext around get_user:")
                for j in range(start, end):
                    print(f"{j+1:4}: {lines[j]}")
                break


if __name__ == "__main__":
    debug_context_truncation()