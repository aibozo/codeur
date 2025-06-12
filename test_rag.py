#!/usr/bin/env python3
"""
Test script for the RAG service.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag_service import RAGService, RAGClient
from src.core.logging import setup_logging
import logging

# Set up logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


def test_rag_service():
    """Test the RAG service functionality."""
    print("\n=== Testing RAG Service ===\n")
    
    # Initialize RAG service
    print("1. Initializing RAG service...")
    rag_service = RAGService(persist_directory=".test_rag")
    rag_client = RAGClient(service=rag_service)
    
    # Check if available
    if rag_client.is_available():
        print("✓ RAG service initialized with embeddings")
    else:
        print("⚠ RAG service initialized but embeddings not available")
        print("  (Set OPENAI_API_KEY for full functionality)")
    
    # Index some files
    print("\n2. Indexing repository files...")
    results = rag_client.index_directory(
        directory="src/request_planner",
        extensions=[".py"]
    )
    
    total_chunks = sum(results.values())
    print(f"✓ Indexed {len(results)} files, {total_chunks} chunks")
    
    # Show stats
    print("\n3. Index statistics:")
    stats = rag_client.get_stats()
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Languages: {stats['languages']}")
    print(f"   Chunk types: {stats['chunk_types']}")
    
    # Test search
    print("\n4. Testing search functionality...")
    
    test_queries = [
        "create plan",
        "LLM integration",
        "context retrieval",
        "search codebase"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = rag_client.search(query, k=3)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result['file_path']}:{result['start_line']} "
                      f"(score: {result['score']:.3f}, type: {result['chunk_type']})")
                if result.get('symbol_name'):
                    print(f"      Symbol: {result['symbol_name']}")
        else:
            print("   No results found")
    
    # Test symbol search
    print("\n5. Testing symbol search...")
    symbol_results = rag_client.find_symbol("RequestPlanner")
    if symbol_results:
        print(f"   Found {len(symbol_results)} matches for 'RequestPlanner'")
        for result in symbol_results[:2]:
            print(f"   - {result['file_path']}:{result['start_line']} "
                  f"({result['chunk_type']})")
    
    # Test context generation
    print("\n6. Testing context generation for LLM...")
    context = rag_client.get_context(
        "How does the Request Planner work?",
        k=5,
        max_tokens=1000
    )
    print(f"   Generated context with {len(context)} characters")
    print(f"   Preview: {context[:200]}...")
    
    print("\n✓ RAG service test completed!")


def test_enhanced_context():
    """Test the enhanced context retriever."""
    print("\n\n=== Testing Enhanced Context Retriever ===\n")
    
    from src.request_planner.enhanced_context import EnhancedContextRetriever
    
    # Initialize enhanced context retriever
    print("1. Initializing enhanced context retriever...")
    retriever = EnhancedContextRetriever(Path("."), use_rag=True)
    
    if retriever.rag_available:
        print("✓ Enhanced context retriever using RAG")
    else:
        print("⚠ Enhanced context retriever falling back to simple search")
    
    # Test context retrieval
    print("\n2. Testing context retrieval...")
    context = retriever.get_context(
        query="Add retry logic to fetch_data function",
        intent={"type": "add_feature", "feature": "retry logic"}
    )
    
    print(f"   Context retrieved:")
    print(f"   - Relevant files: {len(context.get('relevant_files', []))}")
    print(f"   - Snippets: {len(context.get('snippets', []))}")
    print(f"   - Using RAG: {context.get('using_rag', False)}")
    
    if context.get('snippets'):
        print(f"\n   Sample snippet:")
        snippet = context['snippets'][0]
        print(f"   File: {snippet['file']}:{snippet['line']}")
        print(f"   Type: {snippet.get('type', 'unknown')}")
        if snippet.get('symbol'):
            print(f"   Symbol: {snippet['symbol']}")
    
    print("\n✓ Enhanced context test completed!")


if __name__ == "__main__":
    test_rag_service()
    test_enhanced_context()