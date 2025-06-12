#!/usr/bin/env python3
"""
Debug what context the coding agent actually sees.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.context_gatherer import ContextGatherer
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService


def debug_context():
    """See what context is provided to the LLM."""
    
    print("=== Debugging Context Format ===\n")
    
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
    
    print(f"Context contains {len(context.file_snippets)} file snippets\n")
    
    for file_path, content in context.file_snippets.items():
        print(f"=== File: {file_path} ===")
        print("Content format:")
        print("-" * 60)
        # Show first 20 lines
        lines = content.split('\n')[:20]
        for i, line in enumerate(lines):
            print(f"{i}: {repr(line)}")
        print("-" * 60)
        print()
        
        # Check if line numbers are included
        has_line_numbers = any(line.strip().startswith(str(i)) for i, line in enumerate(lines))
        print(f"Has line numbers in content: {has_line_numbers}")
        print()


if __name__ == "__main__":
    debug_context()