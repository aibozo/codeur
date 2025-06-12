# RAG Service Implementation Plan

## Overview

The RAG (Retrieval-Augmented Generation) Service is a critical component that provides intelligent code search and context retrieval for all agents in the system. Currently, we have a basic keyword search implementation that needs to be upgraded to a full-featured RAG system.

## Current State vs Target State

### Current Implementation (10% Complete)
- **Simple keyword search** in `context.py`
- **File traversal** with basic filtering
- **Line-by-line scoring** based on keyword matches
- **No persistence** - searches entire codebase each time
- **No semantic understanding** - exact match only

### Target Specification (from rag_service.txt)
- **Vector database** (Qdrant) for semantic search
- **Hybrid search** combining dense vectors + BM25 sparse search
- **AST-based chunking** using tree-sitter
- **Multi-language support**
- **gRPC/REST API** for service communication
- **Persistent storage** with PostgreSQL + SQLite FTS
- **Incremental indexing** triggered by Git hooks
- **Embedding service** (OpenAI or local model)
- **Reranking** for result quality

## Implementation Phases

### Phase 1: MVP RAG Service (Week 1-2)
Build a functional RAG service that improves on current keyword search.

#### 1.1 Basic Vector Search
- [ ] Add vector database (start with ChromaDB for simplicity)
- [ ] Implement embedding generation using OpenAI
- [ ] Create simple chunking strategy (function/class level)
- [ ] Build basic similarity search

#### 1.2 Service Architecture
- [ ] Create standalone RAG service module
- [ ] Add FastAPI endpoints for search operations
- [ ] Implement simple client for Request Planner
- [ ] Add caching layer for embeddings

#### 1.3 Enhanced Context Retrieval
- [ ] Combine vector search with keyword search
- [ ] Implement basic reranking
- [ ] Add snippet extraction with context
- [ ] Support filtering by file type/path

### Phase 2: Production RAG (Week 3-4)
Upgrade to production-ready architecture.

#### 2.1 Qdrant Integration
- [ ] Replace ChromaDB with Qdrant
- [ ] Implement multi-vector collections
- [ ] Add proper metadata handling
- [ ] Support incremental updates

#### 2.2 Hybrid Search
- [ ] Add SQLite FTS5 for BM25 search
- [ ] Implement alpha-weighted fusion
- [ ] Add query expansion
- [ ] Optimize search performance

#### 2.3 AST-Based Chunking
- [ ] Integrate tree-sitter for Python
- [ ] Add symbol-level chunking
- [ ] Support multiple languages
- [ ] Handle edge cases (large files, binary files)

### Phase 3: Full Specification (Week 5-6)
Complete remaining specification requirements.

#### 3.1 Ingestion Pipeline
- [ ] Add Celery workers for async processing
- [ ] Implement Git hook integration
- [ ] Add file watching with watchdog
- [ ] Support batch ingestion

#### 3.2 Advanced Features
- [ ] Add PostgreSQL for metadata
- [ ] Implement Redis caching
- [ ] Add gRPC interface
- [ ] Support streaming responses

## MVP Implementation Plan (Immediate)

### Step 1: Create RAG Service Structure
```
src/rag_service/
├── __init__.py
├── service.py          # Main RAG service
├── embeddings.py       # Embedding generation
├── chunker.py          # Code chunking logic
├── vector_store.py     # Vector database interface
├── search.py           # Search algorithms
├── api.py              # FastAPI endpoints
└── client.py           # Client for other services
```

### Step 2: Add Dependencies
```toml
# Add to pyproject.toml
chromadb = "^0.4.0"      # Simple vector DB for MVP
fastapi = "^0.100.0"     # Already added
tree-sitter = "^0.20.0"  # For AST parsing
tiktoken = "^0.5.0"      # For token counting
```

### Step 3: Implement Basic Vector Search

```python
# src/rag_service/embeddings.py
class EmbeddingService:
    def __init__(self):
        self.client = OpenAI()
        self.model = "text-embedding-3-small"
    
    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding
```

### Step 4: Create Simple Chunker

```python
# src/rag_service/chunker.py
class CodeChunker:
    def chunk_file(self, content: str, file_path: str) -> List[Chunk]:
        # Start with simple function/class detection
        # Later upgrade to tree-sitter AST parsing
        chunks = []
        # ... implementation
        return chunks
```

### Step 5: Build Search Interface

```python
# src/rag_service/search.py
class HybridSearch:
    def search(
        self, 
        query: str, 
        k: int = 10, 
        alpha: float = 0.5
    ) -> List[SearchResult]:
        # Combine vector and keyword search
        vector_results = self.vector_search(query, k * 2)
        keyword_results = self.keyword_search(query, k * 2)
        return self.merge_results(vector_results, keyword_results, alpha, k)
```

## Integration with Request Planner

### Current Integration Points
1. `context_retriever.get_context()` - Main entry point
2. `context_retriever.search()` - Search functionality
3. `llm.py` - Uses search results for context

### Upgrade Path
1. **Keep backward compatibility** - Maintain current interface
2. **Add RAG client** - New client for enhanced search
3. **Gradual migration** - Switch to RAG when available
4. **Fallback support** - Use simple search if RAG unavailable

## Success Metrics

### MVP Success Criteria
- [ ] 50% improvement in relevant context retrieval
- [ ] Sub-second search response times
- [ ] Support for semantic queries ("functions that handle errors")
- [ ] Better code understanding in LLM responses

### Production Criteria
- [ ] < 200ms p99 latency
- [ ] 90%+ recall on code search
- [ ] Incremental indexing working
- [ ] Multi-language support

## Next Immediate Steps

1. **Create RAG service module structure**
2. **Add vector database dependencies**
3. **Implement basic embedding generation**
4. **Create simple API endpoints**
5. **Update context retriever to use RAG**

## Technical Decisions

### Why Start with ChromaDB?
- Simple to set up (embedded mode)
- Good enough for MVP
- Easy migration path to Qdrant
- Supports filtering and metadata

### Why OpenAI Embeddings First?
- Already have API key configured
- High quality embeddings
- Can switch to local models later
- Consistent with LLM usage

### Why FastAPI?
- Already in dependencies
- Async support built-in
- Easy to add gRPC later
- Good documentation

## Risk Mitigation

1. **Performance Risk**
   - Start with small repos
   - Add caching early
   - Monitor query times

2. **Cost Risk**
   - Cache embeddings aggressively
   - Batch API calls
   - Consider local models for production

3. **Complexity Risk**
   - Keep MVP simple
   - Maintain backward compatibility
   - Incremental improvements