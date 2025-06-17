"""
Enhanced RAG client with retry loops and self-healing capabilities.

Implements intelligent retry strategies for RAG operations based on the
flow patterns, with context-aware fallbacks and recovery mechanisms.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import json

from .client import RAGClient
from ..core.self_healing_coordinator import (
    FailureType, RetryPolicy, RetryStrategy
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class RetryEnhancedRAGClient:
    """
    RAG client with advanced retry and fallback capabilities.
    
    Features:
    - Intelligent retry with backoff
    - Query reformulation on failure
    - Fallback to different search strategies
    - Context caching for repeated queries
    - Degraded mode operation
    """
    
    def __init__(
        self,
        base_client: RAGClient,
        retry_policy: Optional[RetryPolicy] = None
    ):
        """Initialize enhanced RAG client."""
        self.base_client = base_client
        self.retry_policy = retry_policy or RetryPolicy(
            max_attempts=3,
            initial_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
        
        # Cache for recent queries
        self.query_cache: Dict[str, Tuple[List[Any], datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
        
        # Track query patterns for optimization
        self.query_patterns: List[Dict[str, Any]] = []
        
        # Fallback strategies
        self.fallback_strategies = [
            self._search_with_synonyms,
            self._search_with_broader_terms,
            self._search_with_keywords_only,
            self._search_recent_context
        ]
        
    async def search(
        self,
        query: str,
        k: int = 10,
        filter_criteria: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None  # Add for compatibility
    ) -> List[Dict[str, Any]]:
        """
        Enhanced search with retry and fallback strategies.
        
        Flow:
        1. Check cache
        2. Try primary search
        3. On failure, retry with backoff
        4. On repeated failure, try fallback strategies
        5. Return best available results
        """
        # Check cache first
        cached_results = self._get_cached_results(query)
        if cached_results is not None:
            logger.debug(f"Returning cached results for query: {query[:50]}...")
            return cached_results
            
        # Use filters if provided, otherwise filter_criteria
        if filters and not filter_criteria:
            filter_criteria = filters
            
        # Track query for pattern analysis
        self._track_query(query, filter_criteria)
        
        # Primary search with retries
        attempt = 0
        last_error = None
        
        while attempt < self.retry_policy.max_attempts:
            try:
                results = await self._primary_search(query, k, filter_criteria)
                
                # Validate results
                if self._validate_results(results, query):
                    self._cache_results(query, results)
                    return results
                else:
                    logger.warning(f"Invalid results for query: {query[:50]}...")
                    
            except Exception as e:
                last_error = e
                logger.error(f"Search attempt {attempt + 1} failed: {e}")
                
                # Calculate backoff
                if attempt < self.retry_policy.max_attempts - 1:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                    
            attempt += 1
            
        # Primary search failed, try fallback strategies
        logger.warning(f"Primary search failed after {attempt} attempts, trying fallbacks")
        
        for strategy in self.fallback_strategies:
            try:
                results = await strategy(query, k, filter_criteria)
                if results:
                    logger.info(f"Fallback strategy {strategy.__name__} succeeded")
                    self._cache_results(query, results)
                    return results
            except Exception as e:
                logger.error(f"Fallback strategy {strategy.__name__} failed: {e}")
                continue
                
        # All strategies failed, return degraded results
        return await self._get_degraded_results(query, k)
        
    async def _primary_search(
        self,
        query: str,
        k: int,
        filter_criteria: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute primary search through base client."""
        # Base client search is synchronous
        results = self.base_client.search(query, k)
        
        # Convert results to standard format
        if results and hasattr(results[0], 'chunk'):
            return [
                {
                    "content": r.chunk.content,
                    "metadata": r.chunk.metadata if hasattr(r.chunk, 'metadata') else {},
                    "score": r.score
                }
                for r in results
            ]
        return results
        
    def _validate_results(
        self,
        results: List[Dict[str, Any]],
        query: str
    ) -> bool:
        """Validate search results for quality."""
        if not results:
            return False
            
        # Check for minimum relevance
        min_score = 0.3
        relevant_results = [r for r in results if r.get("score", 0) >= min_score]
        
        # Need at least 20% relevant results
        if len(relevant_results) < len(results) * 0.2:
            return False
            
        # Check for diversity (not all from same file)
        unique_files = set(r.get("metadata", {}).get("file", "") for r in results)
        if len(unique_files) == 1 and len(results) > 3:
            return False
            
        return True
        
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with jitter."""
        base_delay = self.retry_policy.initial_delay
        
        if self.retry_policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (self.retry_policy.backoff_factor ** attempt)
        elif self.retry_policy.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * (attempt + 1)
        else:
            delay = base_delay
            
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * 0.1)
        delay += jitter
        
        # Cap at max delay
        return min(delay, self.retry_policy.max_delay)
        
    async def _search_with_synonyms(
        self,
        query: str,
        k: int,
        filter_criteria: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search using synonyms and related terms."""
        # Expand query with common programming synonyms
        synonyms = self._get_synonyms(query)
        
        expanded_query = f"{query} {' '.join(synonyms)}"
        logger.debug(f"Searching with synonyms: {expanded_query[:100]}...")
        
        return await self._primary_search(expanded_query, k, filter_criteria)
        
    def _get_synonyms(self, query: str) -> List[str]:
        """Get programming-related synonyms."""
        # Simple synonym mapping for common terms
        synonym_map = {
            "function": ["method", "def", "func"],
            "class": ["type", "object", "struct"],
            "test": ["unittest", "pytest", "spec"],
            "error": ["exception", "failure", "bug"],
            "import": ["require", "include", "use"],
            "variable": ["var", "parameter", "attribute"],
            "return": ["yield", "output", "result"]
        }
        
        synonyms = []
        query_lower = query.lower()
        
        for term, syns in synonym_map.items():
            if term in query_lower:
                synonyms.extend(syns)
                
        return synonyms[:3]  # Limit to avoid query explosion
        
    async def _search_with_broader_terms(
        self,
        query: str,
        k: int,
        filter_criteria: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search with broader, more general terms."""
        # Extract key concepts
        broad_terms = self._extract_broad_terms(query)
        
        if not broad_terms:
            return []
            
        broad_query = " ".join(broad_terms)
        logger.debug(f"Searching with broader terms: {broad_query}")
        
        # Search with relaxed k to get more results
        results = await self._primary_search(broad_query, k * 2, filter_criteria)
        
        # Re-rank based on original query
        return self._rerank_results(results, query)[:k]
        
    def _extract_broad_terms(self, query: str) -> List[str]:
        """Extract broader conceptual terms."""
        # Remove specific details, keep concepts
        words = query.split()
        
        # Filter out very specific terms (long words, camelCase, etc.)
        broad_terms = []
        for word in words:
            if len(word) <= 10 and not any(c.isupper() for c in word[1:]):
                broad_terms.append(word)
                
        return broad_terms
        
    async def _search_with_keywords_only(
        self,
        query: str,
        k: int,
        filter_criteria: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search using only key programming keywords."""
        keywords = self._extract_keywords(query)
        
        if not keywords:
            return []
            
        keyword_query = " ".join(keywords)
        logger.debug(f"Searching with keywords only: {keyword_query}")
        
        return await self._primary_search(keyword_query, k, filter_criteria)
        
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract programming keywords from query."""
        # Common programming keywords to look for
        keywords = []
        query_lower = query.lower()
        
        # Programming constructs
        constructs = [
            "function", "class", "method", "variable", "import",
            "test", "error", "exception", "return", "async",
            "def", "if", "for", "while", "try", "except"
        ]
        
        for construct in constructs:
            if construct in query_lower:
                keywords.append(construct)
                
        # Also include capitalized words (likely class/function names)
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                keywords.append(word)
                
        return keywords[:5]  # Limit keywords
        
    async def _search_recent_context(
        self,
        query: str,
        k: int,
        filter_criteria: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search only in recently accessed context."""
        # Get recent queries from pattern history
        recent_files = set()
        
        for pattern in self.query_patterns[-10:]:  # Last 10 queries
            cached_query = pattern.get("query", "")
            cached_results = self._get_cached_results(cached_query)
            
            if cached_results:
                for result in cached_results:
                    file_path = result.get("metadata", {}).get("file", "")
                    if file_path:
                        recent_files.add(file_path)
                        
        if not recent_files:
            return []
            
        # Search with file filter
        logger.debug(f"Searching in {len(recent_files)} recent files")
        
        # Modify filter to include only recent files
        enhanced_filter = filter_criteria or {}
        enhanced_filter["file_paths"] = list(recent_files)
        
        return await self._primary_search(query, k, enhanced_filter)
        
    def _rerank_results(
        self,
        results: List[Dict[str, Any]],
        original_query: str
    ) -> List[Dict[str, Any]]:
        """Re-rank results based on original query."""
        # Simple re-ranking based on query term overlap
        query_terms = set(original_query.lower().split())
        
        ranked_results = []
        for result in results:
            content = result.get("content", "").lower()
            
            # Count query term occurrences
            term_count = sum(1 for term in query_terms if term in content)
            
            # Adjust score
            original_score = result.get("score", 0)
            adjusted_score = original_score + (term_count * 0.1)
            
            ranked_result = result.copy()
            ranked_result["score"] = adjusted_score
            ranked_results.append(ranked_result)
            
        # Sort by adjusted score
        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        return ranked_results
        
    async def _get_degraded_results(
        self,
        query: str,
        k: int
    ) -> List[Dict[str, Any]]:
        """Get degraded results when all strategies fail."""
        logger.warning(f"Returning degraded results for query: {query[:50]}...")
        
        # Return any cached results, even if stale
        all_cached = []
        for cached_query, (results, _) in self.query_cache.items():
            # Simple similarity check
            if any(term in cached_query.lower() for term in query.lower().split()):
                all_cached.extend(results)
                
        # Deduplicate and return top k
        seen = set()
        unique_results = []
        
        for result in all_cached:
            content_hash = hash(result.get("content", ""))
            if content_hash not in seen:
                seen.add(content_hash)
                unique_results.append(result)
                
        return unique_results[:k]
        
    def _get_cached_results(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get results from cache if available and fresh."""
        if query not in self.query_cache:
            return None
            
        results, timestamp = self.query_cache[query]
        
        # Check if cache is still fresh
        if datetime.now() - timestamp > self.cache_ttl:
            del self.query_cache[query]
            return None
            
        return results
        
    def _cache_results(self, query: str, results: List[Dict[str, Any]]):
        """Cache search results."""
        self.query_cache[query] = (results, datetime.now())
        
        # Limit cache size
        if len(self.query_cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(
                self.query_cache.items(),
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            
            # Keep only newest 80 entries
            self.query_cache = dict(sorted_items[-80:])
            
    def _track_query(self, query: str, filter_criteria: Optional[Dict[str, Any]]):
        """Track query patterns for analysis."""
        pattern = {
            "query": query,
            "filter": filter_criteria,
            "timestamp": datetime.now()
        }
        
        self.query_patterns.append(pattern)
        
        # Limit pattern history
        if len(self.query_patterns) > 1000:
            self.query_patterns = self.query_patterns[-800:]
            
    async def store_recovery_pattern(
        self,
        failure_context: Dict[str, Any],
        recovery_action: Dict[str, Any],
        success: bool
    ):
        """Store successful recovery patterns for future use."""
        pattern = {
            "failure_type": failure_context.get("error_type", ""),
            "error_message": failure_context.get("error_message", "")[:200],
            "recovery_action": recovery_action,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in RAG for future reference
        try:
            await self.base_client.store_pattern(
                pattern=json.dumps(pattern),
                description=f"Recovery pattern for {failure_context.get('error_type', 'unknown')}",
                tags=["recovery", "self_healing", "rag_retry"]
            )
        except Exception as e:
            logger.error(f"Failed to store recovery pattern: {e}")
            
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get statistics about retry performance."""
        total_queries = len(self.query_patterns)
        cache_size = len(self.query_cache)
        
        # Calculate cache hit rate
        cache_hits = sum(
            1 for p in self.query_patterns[-100:]
            if p.get("query", "") in self.query_cache
        )
        
        cache_hit_rate = cache_hits / min(100, total_queries) if total_queries > 0 else 0
        
        return {
            "total_queries": total_queries,
            "cache_size": cache_size,
            "cache_hit_rate": cache_hit_rate,
            "retry_policy": {
                "max_attempts": self.retry_policy.max_attempts,
                "strategy": self.retry_policy.strategy.value
            }
        }