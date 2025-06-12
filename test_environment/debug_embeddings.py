#!/usr/bin/env python3
"""
Debug embedding dimensions and RAG issues.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import numpy as np

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService
from src.rag_service.embeddings import EmbeddingService
from openai import OpenAI


def test_embedding_dimensions():
    """Test what dimensions the embeddings actually have."""
    
    print("\n=== Testing Embedding Dimensions ===\n")
    
    # Test OpenAI directly
    client = OpenAI()
    
    test_texts = [
        "def get_user(self, user_id):",
        "class APIClient:",
        "import requests"
    ]
    
    print("1. Testing OpenAI API directly:")
    for model in ["text-embedding-3-small", "text-embedding-ada-002"]:
        try:
            print(f"\n  Model: {model}")
            response = client.embeddings.create(
                input=test_texts[0],
                model=model
            )
            embedding = response.data[0].embedding
            print(f"  Dimension: {len(embedding)}")
            print(f"  First 5 values: {embedding[:5]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test with dimensions parameter for text-embedding-3-small
    print("\n2. Testing text-embedding-3-small with dimension parameter:")
    for dim in [384, 512, 1536]:
        try:
            response = client.embeddings.create(
                input=test_texts[0],
                model="text-embedding-3-small",
                dimensions=dim
            )
            embedding = response.data[0].embedding
            print(f"  Requested {dim}D -> Got {len(embedding)}D")
        except Exception as e:
            print(f"  Dimension {dim}: Error - {e}")
    
    # Test our embedding service
    print("\n3. Testing our EmbeddingService:")
    embedding_service = EmbeddingService()
    
    for text in test_texts:
        embedding = embedding_service.embed_text(text)
        if embedding:
            print(f"  Text: '{text[:30]}...' -> {len(embedding)}D")
        else:
            print(f"  Text: '{text[:30]}...' -> Failed")
    
    # Check what's in the vector store
    print("\n4. Checking existing vector store:")
    repo_path = Path(__file__).parent / "test_repo"
    rag_dir = repo_path / ".rag"
    
    if rag_dir.exists():
        rag_service = RAGService(persist_directory=str(rag_dir))
        
        # Get collection info
        try:
            collection = rag_service.vector_store.collection
            count = collection.count()
            print(f"  Collection has {count} items")
            
            # Try to peek at an item
            if count > 0:
                result = collection.peek(1)
                if result and 'embeddings' in result and result['embeddings']:
                    embedding = result['embeddings'][0]
                    print(f"  First embedding dimension: {len(embedding)}")
                    print(f"  Metadata: {result.get('metadatas', [{}])[0]}")
        except Exception as e:
            print(f"  Error checking collection: {e}")


def fix_rag_search():
    """Test fixing the RAG search issues."""
    
    print("\n\n=== Testing RAG Search Fix ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    rag_dir = repo_path / ".rag"
    
    # Create fresh RAG service
    print("1. Creating fresh RAG service...")
    import shutil
    if rag_dir.exists():
        shutil.rmtree(rag_dir)
    
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Index the api_client.py file
    api_file = repo_path / "src/api_client.py"
    print(f"\n2. Indexing {api_file}...")
    
    if api_file.exists():
        chunks = rag_service.index_file(str(api_file))
        print(f"   Indexed {chunks} chunks")
    
    # Test search with different queries
    print("\n3. Testing searches:")
    
    queries = [
        ("get_user", None),
        ("get_user method", None),
        ("get_user", {"file_path": "src/api_client.py"}),
        ("APIClient", {"chunk_type": "class"}),
    ]
    
    for query, filters in queries:
        print(f"\n   Query: '{query}' with filters: {filters}")
        try:
            results = rag_service.search(query, k=3, filters=filters)
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results):
                print(f"     {i+1}. {result['file_path']}:{result['start_line']} - {result.get('symbol_name', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    test_embedding_dimensions()
    fix_rag_search()