#!/usr/bin/env python3
"""
Investigate the 384D vs 1536D embedding dimension error.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService
from src.rag_service.embeddings import EmbeddingService
from src.rag_service.vector_store import VectorStore


def check_collection_dimensions():
    """Check the dimensions of embeddings in the existing collection."""
    
    print("\n=== Checking Existing Collection Dimensions ===\n")
    
    # Check main .rag directory
    rag_dir = Path("/home/riley/Programming/agent/.rag/vector_store")
    if rag_dir.exists():
        print(f"1. Checking main RAG directory: {rag_dir}")
        
        client = chromadb.PersistentClient(
            path=str(rag_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        try:
            collections = client.list_collections()
            print(f"   Found {len(collections)} collections")
            
            for coll in collections:
                print(f"\n   Collection: {coll.name}")
                count = coll.count()
                print(f"   Total items: {count}")
                
                if count > 0:
                    # Peek at some items
                    result = coll.peek(5)
                    if result and 'embeddings' in result and result['embeddings']:
                        for i, emb in enumerate(result['embeddings']):
                            if emb is not None:
                                print(f"   Item {i+1} embedding dimension: {len(emb)}")
                                if 'metadatas' in result and i < len(result['metadatas']):
                                    meta = result['metadatas'][i]
                                    print(f"     File: {meta.get('file_path', 'N/A')}")
                                    print(f"     Created: {meta.get('created_at', 'N/A')}")
                    
                    # Try to get all unique dimensions
                    print("\n   Checking for mixed dimensions...")
                    sample = coll.get(limit=100)
                    if sample and 'embeddings' in sample and sample['embeddings']:
                        dimensions = set()
                        for emb in sample['embeddings']:
                            if emb is not None and isinstance(emb, list):
                                dimensions.add(len(emb))
                        print(f"   Found dimensions: {sorted(dimensions)}")
                        
        except Exception as e:
            print(f"   Error: {e}")
    
    # Check test_repo directory
    test_rag_dir = Path("/home/riley/Programming/agent/test_repo/.rag/vector_store")
    if test_rag_dir.exists():
        print(f"\n2. Checking test_repo RAG directory: {test_rag_dir}")
        
        client = chromadb.PersistentClient(
            path=str(test_rag_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            collections = client.list_collections()
            print(f"   Found {len(collections)} collections")
            
            for coll in collections:
                print(f"   Collection: {coll.name}")
                print(f"   Total items: {coll.count()}")
                
        except Exception as e:
            print(f"   Error: {e}")


def test_embedding_search():
    """Test embedding and search to reproduce the error."""
    
    print("\n\n=== Testing Embedding and Search ===\n")
    
    # Create embedding service
    embedding_service = EmbeddingService()
    
    # Test creating embeddings
    test_text = "def get_user(self, user_id):"
    embedding = embedding_service.embed_text(test_text)
    print(f"1. Created embedding dimension: {len(embedding) if embedding else 'None'}")
    
    # Try direct ChromaDB operations to avoid VectorStore initialization conflicts
    print("\n2. Testing search directly with ChromaDB...")
    try:
        client = chromadb.PersistentClient(
            path="/home/riley/Programming/agent/.rag/vector_store",
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        collection = client.get_collection("code_chunks")
        
        print(f"   Attempting search with {len(embedding)}D embedding...")
        results = collection.query(
            query_embeddings=[embedding],
            n_results=5
        )
        print(f"   Search successful! Found {len(results['ids'][0]) if results['ids'] else 0} results")
        
    except Exception as e:
        print(f"   Search failed with error: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # This is likely where we'll see the dimension mismatch error
        if "dimension" in str(e).lower():
            print("\n   *** DIMENSION MISMATCH ERROR FOUND! ***")
            print(f"   The collection expects a different dimension than {len(embedding)}")
        
        # Try to get more details about the error
        import traceback
        print("\n   Full traceback:")
        traceback.print_exc()


def check_embedding_model_config():
    """Check if there's any configuration that might cause 384D embeddings."""
    
    print("\n\n=== Checking Embedding Model Configuration ===\n")
    
    # Check environment variables
    import os
    print("1. Environment variables:")
    for key, value in os.environ.items():
        if 'EMBED' in key.upper() or 'DIM' in key.upper():
            print(f"   {key}={value}")
    
    # Check if there's any cached model info
    print("\n2. Checking for model configuration files...")
    
    # Look for any config files
    for config_pattern in ["*config*.json", "*config*.yaml", "*settings*.json"]:
        config_files = list(Path("/home/riley/Programming/agent").glob(f"**/{config_pattern}"))
        for cf in config_files[:5]:  # Limit to first 5
            if '.mypy_cache' not in str(cf) and '__pycache__' not in str(cf):
                print(f"   Found: {cf}")


if __name__ == "__main__":
    check_collection_dimensions()
    test_embedding_search()
    check_embedding_model_config()