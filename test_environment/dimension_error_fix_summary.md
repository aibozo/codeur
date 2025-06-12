# RAG Service Dimension Mismatch Error Fix

## Problem Summary

The error "Collection expecting embedding with dimension of 1536, got 384" was occurring during keyword searches in the RAG service.

### Root Cause

1. The RAG service uses OpenAI's `text-embedding-3-small` model which produces **1536-dimensional** embeddings
2. The `keyword_search` method in `vector_store.py` was using ChromaDB's `query_texts` parameter
3. ChromaDB's `query_texts` automatically creates embeddings using its default embedding function
4. ChromaDB's default embedding function produces **384-dimensional** embeddings
5. This caused a dimension mismatch when searching a collection indexed with 1536D embeddings

### Code Location

The error occurred in `/home/riley/Programming/agent/src/rag_service/vector_store.py` at line 226:

```python
# Original problematic code:
results = self.collection.query(
    query_texts=[query],  # This creates 384D embeddings!
    n_results=k,
    where=where if where else None
)
```

## Solution Implemented

### 1. Modified Keyword Search Implementation

Instead of using ChromaDB's `query_texts` (which creates embeddings), we now:
- Retrieve all documents matching the filters using `collection.get()`
- Perform text-based keyword matching in Python
- Score results based on word occurrences
- Return top-k results without creating any embeddings

### 2. Code Changes

The `keyword_search` method was completely rewritten to:

```python
# New implementation:
all_results = self.collection.get(
    where=where if where else None,
    include=["documents", "metadatas"]
)

# Then perform keyword matching on the retrieved documents
# Score based on word occurrences and exact phrase matches
# Return top-k results
```

### 3. Additional Improvements

- Added `embedding_function=None` when creating new collections to prevent ChromaDB from using a default embedding function
- Added detailed documentation explaining why we don't use `query_texts`
- Implemented a proper keyword scoring algorithm

## Benefits

1. **No More Dimension Errors**: Keyword search no longer creates embeddings, avoiding dimension mismatches
2. **Consistent Behavior**: All embeddings in the system now use the same 1536D model
3. **Better Control**: We have full control over the keyword matching logic
4. **Performance**: Keyword search is now a simple text matching operation without embedding generation overhead

## Testing

The fix was tested with:
1. New collections - works perfectly
2. Existing collections - works without errors
3. Hybrid search (which uses keyword search internally) - works correctly

The keyword search now successfully finds relevant code chunks based on text matching without any embedding dimension issues.