#!/usr/bin/env python3
"""
Find any 384D embeddings in the collection.
"""

import chromadb
from chromadb.config import Settings
import numpy as np

def find_dimension_issues():
    """Find all unique embedding dimensions in the collection."""
    
    print("=== Searching for 384D Embeddings ===\n")
    
    client = chromadb.PersistentClient(
        path="/home/riley/Programming/agent/.rag/vector_store",
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )
    
    collection = client.get_collection("code_chunks")
    total = collection.count()
    print(f"Total items in collection: {total}")
    
    # Get all items in batches
    batch_size = 50
    all_dimensions = {}
    items_by_dimension = {}
    
    for offset in range(0, total, batch_size):
        limit = min(batch_size, total - offset)
        print(f"\nChecking items {offset} to {offset + limit}...")
        
        # Get batch
        result = collection.get(
            limit=limit,
            offset=offset,
            include=["embeddings", "metadatas", "documents"]
        )
        
        if result and 'embeddings' in result:
            for i, emb in enumerate(result['embeddings']):
                if emb is not None:
                    dim = len(emb)
                    all_dimensions[dim] = all_dimensions.get(dim, 0) + 1
                    
                    # Track items with non-1536 dimensions
                    if dim != 1536:
                        if dim not in items_by_dimension:
                            items_by_dimension[dim] = []
                        
                        item_info = {
                            'id': result['ids'][i] if 'ids' in result else 'unknown',
                            'file': result['metadatas'][i].get('file_path', 'unknown') if 'metadatas' in result else 'unknown',
                            'content_preview': result['documents'][i][:100] if 'documents' in result else 'unknown'
                        }
                        items_by_dimension[dim].append(item_info)
    
    print("\n=== Summary ===")
    print(f"Total unique dimensions found: {len(all_dimensions)}")
    for dim, count in sorted(all_dimensions.items()):
        print(f"  {dim}D: {count} items ({count/total*100:.1f}%)")
    
    # Show details of non-1536D items
    if items_by_dimension:
        print("\n=== Non-1536D Items ===")
        for dim, items in items_by_dimension.items():
            print(f"\n{dim}D embeddings ({len(items)} items):")
            for item in items[:5]:  # Show first 5
                print(f"  - ID: {item['id']}")
                print(f"    File: {item['file']}")
                print(f"    Content: {item['content_preview']}...")
                print()


def test_search_with_different_dimensions():
    """Test searching with different dimension embeddings."""
    
    print("\n\n=== Testing Search with Different Dimensions ===\n")
    
    client = chromadb.PersistentClient(
        path="/home/riley/Programming/agent/.rag/vector_store",
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )
    
    collection = client.get_collection("code_chunks")
    
    # Test with different dimension vectors
    for dim in [384, 512, 1536]:
        print(f"\nTesting with {dim}D embedding:")
        
        # Create a random embedding of the specified dimension
        test_embedding = np.random.rand(dim).tolist()
        
        try:
            results = collection.query(
                query_embeddings=[test_embedding],
                n_results=1
            )
            print(f"  ✓ Search successful with {dim}D embedding")
        except Exception as e:
            print(f"  ✗ Search failed with {dim}D embedding")
            print(f"    Error: {e}")


if __name__ == "__main__":
    find_dimension_issues()
    test_search_with_different_dimensions()