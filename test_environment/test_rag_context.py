#!/usr/bin/env python3
"""
Test RAG-based context gathering.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService, RAGClient
from src.proto_gen import messages_pb2
import logging

logging.basicConfig(level=logging.INFO)


def test_rag_indexing():
    """Test RAG indexing and search."""
    
    print("=== Testing RAG Indexing and Search ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Initialize RAG
    rag_service = RAGService(persist_directory=str(repo_path / ".rag"))
    
    # Index the api_client.py file
    api_file = repo_path / "src" / "api_client.py"
    print(f"Indexing {api_file}...")
    
    chunks_indexed = rag_service.index_file(str(api_file))
    print(f"Indexed {chunks_indexed} chunks\n")
    
    # Create client
    rag_client = RAGClient(service=rag_service)
    
    # Search for get_user method
    print("Searching for 'get_user method docstring'...")
    results = rag_client.search(
        query="get_user method docstring API endpoint",
        k=5
    )
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results):
        # Result is already a dict from to_dict() method
        print(f"\n{i+1}. File: {result.get('file_path')}")
        print(f"   Lines: {result.get('start_line')}-{result.get('end_line')}")
        print(f"   Type: {result.get('chunk_type')}")
        print(f"   Score: {result.get('score', 0):.3f}")
        print(f"   Content preview:")
        content = result.get('content', '')[:200]
        print(f"   {content}...")
    
    # Get full context for the best result
    if results:
        best = results[0]
        print(f"\n\n=== BEST MATCH FULL CONTENT ===")
        print(f"File: {best.get('file_path')}")
        print(f"Lines: {best.get('start_line')}-{best.get('end_line')}")
        print("-" * 60)
        print(best.get('content', ''))
        print("-" * 60)
        
        # Show with line numbers
        content = best.get('content', '')
        start_line = best.get('start_line', 1)
        
        print(f"\n=== WITH LINE NUMBERS ===")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            print(f"{start_line + i:4d}: {line}")


if __name__ == "__main__":
    test_rag_indexing()