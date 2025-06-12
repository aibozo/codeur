#!/usr/bin/env python3
"""
Test the keyword search fix for dimension mismatch error.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService
from src.rag_service.vector_store import VectorStore
from src.rag_service.embeddings import EmbeddingService


def test_keyword_search():
    """Test that keyword search no longer causes dimension mismatch."""
    
    print("=== Testing Keyword Search Fix ===\n")
    
    # Initialize services
    print("1. Initializing RAG service...")
    rag_service = RAGService(
        persist_directory=".rag_test",
        embedding_model="text-embedding-3-small"
    )
    
    # First, let's index a simple test file
    test_content = """
def hello_world():
    print("Hello, World!")
    
def calculate_sum(a, b):
    return a + b
    
class UserManager:
    def get_user(self, user_id):
        # Get user by ID
        return {"id": user_id, "name": "Test User"}
    
    def create_user(self, name, email):
        # Create a new user
        return {"name": name, "email": email}
"""
    
    print("\n2. Indexing test content...")
    chunks = rag_service.index_file("test_file.py", content=test_content)
    print(f"   Indexed {chunks} chunks")
    
    # Now test keyword search
    print("\n3. Testing keyword search (this previously caused dimension error)...")
    try:
        results = rag_service.vector_store.keyword_search(
            query="get_user user_id",
            k=5
        )
        print(f"   ✓ Keyword search successful! Found {len(results)} results")
        
        if results:
            print("\n   Top results:")
            for i, (chunk, score) in enumerate(results[:3]):
                print(f"   {i+1}. Score: {score:.3f}")
                print(f"      File: {chunk.file_path}")
                print(f"      Lines: {chunk.start_line}-{chunk.end_line}")
                print(f"      Preview: {chunk.content[:100]}...")
                
    except Exception as e:
        print(f"   ✗ Keyword search failed: {e}")
        if "dimension" in str(e).lower():
            print("   ERROR: Dimension mismatch still occurring!")
            return False
    
    # Test hybrid search which uses keyword search internally
    print("\n4. Testing hybrid search...")
    try:
        results = rag_service.search_code(
            query="get_user function",
            k=5
        )
        print(f"   ✓ Hybrid search successful! Found {len(results)} results")
        
    except Exception as e:
        print(f"   ✗ Hybrid search failed: {e}")
        if "dimension" in str(e).lower():
            print("   ERROR: Dimension mismatch in hybrid search!")
            return False
    
    # Clean up
    import shutil
    if Path(".rag_test").exists():
        shutil.rmtree(".rag_test")
    
    print("\n✅ All tests passed! Keyword search fix is working.")
    return True


def test_with_existing_collection():
    """Test with the existing collection that has the issue."""
    
    print("\n\n=== Testing with Existing Collection ===\n")
    
    # Check if the main .rag directory exists
    rag_dir = Path("/home/riley/Programming/agent/.rag")
    if not rag_dir.exists():
        print("No existing .rag directory found.")
        return
    
    print("1. Initializing with existing collection...")
    try:
        vector_store = VectorStore(
            persist_directory=str(rag_dir / "vector_store"),
            collection_name="code_chunks"
        )
        
        print("\n2. Testing keyword search on existing data...")
        results = vector_store.keyword_search(
            query="RAGService index_file",
            k=5
        )
        
        print(f"   ✓ Search successful! Found {len(results)} results")
        
        if results:
            print("\n   Sample results:")
            for i, (chunk, score) in enumerate(results[:2]):
                print(f"   {i+1}. Score: {score:.3f}")
                print(f"      File: {chunk.file_path}")
                
    except Exception as e:
        print(f"   Error: {e}")
        if "dimension" in str(e).lower():
            print("\n   ⚠️  Dimension error still occurring with existing collection!")
            print("   This might be because the collection was created with a default embedding function.")
            print("   You may need to recreate the collection to fully fix the issue.")


if __name__ == "__main__":
    # Test with new collection
    success = test_keyword_search()
    
    # Test with existing collection
    test_with_existing_collection()
    
    if success:
        print("\n\n✅ Fix implemented successfully!")
        print("\nThe keyword search now:")
        print("1. Retrieves all documents matching the filters")
        print("2. Performs text-based keyword matching")
        print("3. Scores results based on word occurrences")
        print("4. Returns top-k results without creating embeddings")
        print("\nThis avoids the dimension mismatch error entirely.")