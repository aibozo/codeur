#!/usr/bin/env python3
"""
Test smart context gathering with RAG.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.context_gatherer_v2 import SmartContextGatherer
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)


def test_smart_context():
    """Test smart context gathering."""
    
    print("=== Testing Smart Context Gathering ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Create a test task
    task = messages_pb2.CodingTask()
    task.id = "test-001"
    task.goal = "Update the docstring of the get_user method to say 'Fetch user data from the API endpoint.'"
    task.paths.append("src/api_client.py")
    
    # Initialize RAG
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # First, let's index the test repo if needed
    print("Indexing test repository...")
    from src.rag_service.index import index_repository
    index_repository(str(repo_path), rag_service)
    print("Indexing complete!\n")
    
    rag_client = RAGClient(service=rag_service)
    
    # Create smart gatherer
    gatherer = SmartContextGatherer(str(repo_path), rag_client)
    
    # Gather context
    print("Gathering context...")
    context = gatherer.gather_context(task, max_chunks=10)
    
    print(f"\nContext gathered:")
    print(f"- Token count: {context.token_count}")
    print(f"- RAG chunks: {len(context.blob_contents)}")
    print(f"- File skeletons: {len(context.file_snippets)}")
    print(f"- Related functions: {len(context.related_functions)}")
    
    # Show what was gathered
    print("\n=== RAG CHUNKS (semantically relevant) ===")
    for blob_id, content in context.blob_contents.items():
        print(f"\nChunk: {blob_id}")
        print("-" * 40)
        print(content)
        print("-" * 40)
    
    print("\n=== FILE SKELETONS ===")
    for path, skeleton in context.file_snippets.items():
        print(f"\nFile: {path}")
        print("-" * 40)
        print(skeleton)
        print("-" * 40)
    
    # Show the full prompt context
    print("\n=== FULL PROMPT CONTEXT (what o3 would see) ===")
    prompt_context = context.to_prompt_context()
    print(prompt_context)
    
    # Compare sizes
    print("\n=== CONTEXT STATS ===")
    print(f"Total prompt context size: {len(prompt_context)} characters")
    print(f"Estimated tokens: {len(prompt_context) // 4}")
    
    # Test searching for the specific method
    print("\n=== TESTING SPECIFIC SEARCH ===")
    results = rag_client.search(
        query="get_user method docstring",
        k=5
    )
    
    print(f"\nFound {len(results)} results for 'get_user method docstring':")
    for i, result in enumerate(results):
        chunk = result.get("chunk", {})
        print(f"\n{i+1}. {chunk.get('file_path')}:{chunk.get('start_line')}-{chunk.get('end_line')}")
        print(f"   Type: {chunk.get('chunk_type')}")
        print(f"   Symbol: {chunk.get('symbol_name')}")
        print(f"   Score: {result.get('score', 0):.3f}")
        print(f"   Preview: {chunk.get('content', '')[:100]}...")


if __name__ == "__main__":
    test_smart_context()