"""
Search algorithms for the RAG service.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from collections import defaultdict
import re

from .models import CodeChunk, SearchResult, SearchRequest
from .embeddings import EmbeddingService
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Implements hybrid search combining vector similarity and keyword matching.
    """
    
    def __init__(self, 
                 vector_store: VectorStore,
                 embedding_service: EmbeddingService):
        """
        Initialize the hybrid search.
        
        Args:
            vector_store: Vector store instance
            embedding_service: Embedding service instance
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def search(self, request: SearchRequest) -> List[SearchResult]:
        """
        Perform hybrid search.
        
        Args:
            request: Search request
            
        Returns:
            List of search results
        """
        # Generate query embedding if embedding service is available
        query_embedding = None
        if self.embedding_service.enabled:
            query_embedding = self.embedding_service.embed_text(request.query)
        
        # Perform searches
        vector_results = []
        keyword_results = []
        
        # Vector search if embedding available
        if query_embedding:
            vector_results = self.vector_store.search(
                query_embedding=query_embedding,
                k=request.k * 2,  # Get more results for merging
                filters=request.filters
            )
        
        # Keyword search
        keyword_results = self.vector_store.keyword_search(
            query=request.query,
            k=request.k * 2,
            filters=request.filters
        )
        
        # Merge results
        merged_results = self._merge_results(
            vector_results=vector_results,
            keyword_results=keyword_results,
            alpha=request.alpha,
            k=request.k
        )
        
        # Convert to SearchResult objects
        search_results = []
        for chunk, score in merged_results:
            # Extract highlights
            highlights = self._extract_highlights(chunk.content, request.query)
            
            result = SearchResult(
                chunk=chunk,
                score=score,
                match_type="hybrid" if vector_results and keyword_results else 
                          "vector" if vector_results else "keyword",
                highlights=highlights
            )
            search_results.append(result)
        
        return search_results
    
    def _merge_results(self,
                      vector_results: List[Tuple[CodeChunk, float]],
                      keyword_results: List[Tuple[CodeChunk, float]],
                      alpha: float,
                      k: int) -> List[Tuple[CodeChunk, float]]:
        """
        Merge vector and keyword search results.
        
        Uses reciprocal rank fusion with alpha weighting.
        """
        # Build score maps
        vector_scores = {chunk.id: score for chunk, score in vector_results}
        keyword_scores = {chunk.id: score for chunk, score in keyword_results}
        
        # Collect all unique chunks
        all_chunks = {}
        for chunk, _ in vector_results:
            all_chunks[chunk.id] = chunk
        for chunk, _ in keyword_results:
            all_chunks[chunk.id] = chunk
        
        # Calculate combined scores
        combined_scores = {}
        for chunk_id, chunk in all_chunks.items():
            vector_score = vector_scores.get(chunk_id, 0.0)
            keyword_score = keyword_scores.get(chunk_id, 0.0)
            
            # Weighted combination
            combined_score = alpha * vector_score + (1 - alpha) * keyword_score
            combined_scores[chunk_id] = (chunk, combined_score)
        
        # Sort by score
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top k
        return sorted_results[:k]
    
    def _extract_highlights(self, content: str, query: str, context_chars: int = 100) -> List[str]:
        """
        Extract highlighted snippets from content.
        
        Args:
            content: Full content
            query: Search query
            context_chars: Characters of context around match
            
        Returns:
            List of highlighted snippets
        """
        highlights = []
        
        # Split query into words
        query_words = query.lower().split()
        
        # Find matches for each word
        for word in query_words:
            if len(word) < 3:  # Skip short words
                continue
            
            # Case-insensitive search
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            
            for match in pattern.finditer(content):
                start = max(0, match.start() - context_chars)
                end = min(len(content), match.end() + context_chars)
                
                # Extract snippet
                snippet = content[start:end]
                
                # Add ellipsis if truncated
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                
                # Highlight the matched word
                highlighted = pattern.sub(f"**{match.group()}**", snippet)
                highlights.append(highlighted)
                
                # Limit highlights
                if len(highlights) >= 3:
                    break
            
            if len(highlights) >= 3:
                break
        
        return highlights


class CodeSearch:
    """
    High-level search interface for the RAG service.
    """
    
    def __init__(self,
                 vector_store: VectorStore,
                 embedding_service: EmbeddingService):
        """
        Initialize the code search.
        
        Args:
            vector_store: Vector store instance
            embedding_service: Embedding service instance
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.hybrid_search = HybridSearch(vector_store, embedding_service)
    
    def search(self, 
               query: str,
               k: int = 10,
               filters: Optional[Dict[str, Any]] = None,
               search_type: str = "hybrid") -> List[SearchResult]:
        """
        Search for code.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            search_type: Type of search ("hybrid", "vector", "keyword")
            
        Returns:
            List of search results
        """
        # Create search request
        request = SearchRequest(
            query=query,
            k=k,
            filters=filters or {},
            alpha=0.5 if search_type == "hybrid" else 
                  1.0 if search_type == "vector" else 0.0
        )
        
        # Perform search
        return self.hybrid_search.search(request)
    
    def find_similar(self, 
                    chunk: CodeChunk,
                    k: int = 10,
                    filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Find similar code chunks.
        
        Args:
            chunk: Reference chunk
            k: Number of results
            filters: Optional filters
            
        Returns:
            List of similar chunks
        """
        # Generate embedding for the chunk if needed
        if chunk.embedding is None and self.embedding_service.enabled:
            chunk.embedding = self.embedding_service.embed_text(
                chunk.text_for_embedding
            )
        
        if chunk.embedding is None:
            # Fall back to keyword search
            return self.search(
                query=chunk.content[:200],  # Use first 200 chars
                k=k,
                filters=filters,
                search_type="keyword"
            )
        
        # Vector search
        results = self.vector_store.search(
            query_embedding=chunk.embedding,
            k=k + 1,  # Get one extra to exclude self
            filters=filters
        )
        
        # Convert to SearchResult and exclude self
        search_results = []
        for result_chunk, score in results:
            if result_chunk.id != chunk.id:
                search_results.append(SearchResult(
                    chunk=result_chunk,
                    score=score,
                    match_type="vector"
                ))
        
        return search_results[:k]
    
    def search_by_symbol(self,
                        symbol_name: str,
                        filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for a specific symbol (function, class, etc).
        
        Args:
            symbol_name: Name of the symbol
            filters: Optional filters
            
        Returns:
            List of search results
        """
        # Add symbol name to filters
        if filters is None:
            filters = {}
        
        # Search with symbol-focused query
        query = f"function {symbol_name} class {symbol_name} def {symbol_name}"
        
        return self.search(
            query=query,
            k=20,
            filters=filters,
            search_type="hybrid"
        )