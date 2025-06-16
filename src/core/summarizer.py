"""
Summarization service for generating concise summaries of text content.

This service provides cost-effective summarization using smaller language models
like GPT-4o-mini, with support for batch processing and caching.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
from collections import defaultdict

try:
    from ..llm import LLMClient
except ImportError:
    # Create a simple mock if LLM module not available
    class LLMClient:
        async def complete(self, **kwargs):
            return type('Response', (), {'content': 'Mock response'})
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class SummarizationRequest:
    """Request for summarization."""
    id: str
    content: str
    max_tokens: int = 100
    preserve_code: bool = True
    preserve_decisions: bool = True
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SummarizationResult:
    """Result of summarization."""
    request_id: str
    summary: str
    token_count: int
    quality_score: float = 1.0
    cost: float = 0.0
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SummarizationMetrics:
    """Metrics for tracking summarization performance."""
    total_requests: int = 0
    total_tokens_processed: int = 0
    total_tokens_generated: int = 0
    total_cost: float = 0.0
    avg_quality_score: float = 1.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    
    def add_result(self, result: SummarizationResult, input_tokens: int):
        """Update metrics with a new result."""
        self.total_requests += 1
        self.total_tokens_processed += input_tokens
        self.total_tokens_generated += result.token_count
        self.total_cost += result.cost
        
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class SummarizationService:
    """
    Service for generating summaries using language models.
    
    Features:
    - Configurable model selection
    - Batch processing for efficiency
    - Caching to avoid redundant API calls
    - Cost tracking and budgeting
    - Quality scoring
    """
    
    def __init__(self, 
                 llm_client: Optional[LLMClient] = None,
                 model: str = "gpt-4o-mini",
                 cache_ttl_hours: int = 24,
                 max_batch_size: int = 10):
        """
        Initialize the summarization service.
        
        Args:
            llm_client: LLM client for API calls
            model: Model to use for summarization
            cache_ttl_hours: Cache time-to-live in hours
            max_batch_size: Maximum batch size for processing
        """
        self.llm_client = llm_client
        self.model = model
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.max_batch_size = max_batch_size
        
        # Cache for summaries
        self._cache: Dict[str, Tuple[SummarizationResult, datetime]] = {}
        
        # Metrics
        self.metrics = SummarizationMetrics()
        
        # Batch processing queue
        self._pending_requests: List[SummarizationRequest] = []
        self._processing = False
        
        logger.info(f"Initialized summarization service with model {model}")
        
    def _get_cache_key(self, content: str, max_tokens: int) -> str:
        """Generate cache key for content."""
        key_data = f"{content}:{max_tokens}:{self.model}"
        return hashlib.sha256(key_data.encode()).hexdigest()
        
    def _check_cache(self, request: SummarizationRequest) -> Optional[SummarizationResult]:
        """Check if summary exists in cache."""
        cache_key = self._get_cache_key(request.content, request.max_tokens)
        
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                self.metrics.cache_hits += 1
                logger.debug(f"Cache hit for request {request.id}")
                # Return a copy with updated request_id
                return SummarizationResult(
                    request_id=request.id,
                    summary=result.summary,
                    token_count=result.token_count,
                    quality_score=result.quality_score,
                    cost=result.cost,
                    duration_ms=result.duration_ms,
                    timestamp=result.timestamp
                )
            else:
                # Expired entry
                del self._cache[cache_key]
                
        self.metrics.cache_misses += 1
        return None
        
    def _cache_result(self, request: SummarizationRequest, result: SummarizationResult):
        """Cache summarization result."""
        cache_key = self._get_cache_key(request.content, request.max_tokens)
        self._cache[cache_key] = (result, datetime.now())
        
    async def summarize(self, 
                       content: str,
                       max_tokens: int = 100,
                       preserve_code: bool = True,
                       preserve_decisions: bool = True,
                       context: Optional[str] = None) -> SummarizationResult:
        """
        Generate a summary of the provided content.
        
        Args:
            content: Content to summarize
            max_tokens: Maximum tokens for summary
            preserve_code: Whether to preserve code blocks
            preserve_decisions: Whether to preserve decisions
            context: Additional context for summarization
            
        Returns:
            SummarizationResult with the summary
        """
        request = SummarizationRequest(
            id=hashlib.sha256(content.encode()).hexdigest()[:8],
            content=content,
            max_tokens=max_tokens,
            preserve_code=preserve_code,
            preserve_decisions=preserve_decisions,
            context=context
        )
        
        # Check cache first
        cached = self._check_cache(request)
        if cached:
            return cached
            
        # Process immediately if no LLM client
        if not self.llm_client:
            return self._create_mock_summary(request)
            
        # Process the request
        result = await self._process_single_request(request)
        
        # Cache the result
        self._cache_result(request, result)
        
        return result
        
    async def summarize_batch(self, 
                            contents: List[str],
                            max_tokens: int = 100,
                            **kwargs) -> List[SummarizationResult]:
        """
        Summarize multiple contents in batch for efficiency.
        
        Args:
            contents: List of contents to summarize
            max_tokens: Maximum tokens per summary
            **kwargs: Additional arguments for summarization
            
        Returns:
            List of summarization results
        """
        requests = [
            SummarizationRequest(
                id=f"batch_{i}",
                content=content,
                max_tokens=max_tokens,
                **kwargs
            )
            for i, content in enumerate(contents)
        ]
        
        # Check cache and separate cached vs uncached
        results = []
        uncached_requests = []
        
        for request in requests:
            cached = self._check_cache(request)
            if cached:
                results.append(cached)
            else:
                uncached_requests.append(request)
                
        # Process uncached requests
        if uncached_requests:
            if not self.llm_client:
                # Mock processing
                new_results = [self._create_mock_summary(req) for req in uncached_requests]
            else:
                # Batch process
                new_results = await self._process_batch(uncached_requests)
                
            # Cache results
            for req, res in zip(uncached_requests, new_results):
                self._cache_result(req, res)
                
            results.extend(new_results)
            
        return results
        
    async def _process_single_request(self, request: SummarizationRequest) -> SummarizationResult:
        """Process a single summarization request."""
        start_time = datetime.now()
        
        try:
            # Build the prompt
            prompt = self._build_prompt(request)
            
            # Estimate input tokens (rough estimate)
            input_tokens = len(request.content) // 4
            
            # Make API call
            response = await self.llm_client.complete(
                prompt=prompt,
                model=self.model,
                max_tokens=request.max_tokens,
                temperature=0.3  # Lower temperature for consistent summaries
            )
            
            summary = response.content
            output_tokens = len(summary) // 4
            
            # Calculate cost (using GPT-4o-mini pricing)
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Simple quality score based on length ratio
            quality_score = min(1.0, len(summary) / len(request.content) * 10)
            
            result = SummarizationResult(
                request_id=request.id,
                summary=summary,
                token_count=output_tokens,
                quality_score=quality_score,
                cost=cost,
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            self.metrics.add_result(result, input_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            self.metrics.errors += 1
            
            # Return a fallback summary
            return SummarizationResult(
                request_id=request.id,
                summary=request.content[:request.max_tokens * 4],  # Rough truncation
                token_count=request.max_tokens,
                quality_score=0.5,
                cost=0.0,
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
    async def _process_batch(self, requests: List[SummarizationRequest]) -> List[SummarizationResult]:
        """Process multiple requests in batch."""
        # For now, process sequentially
        # TODO: Implement true batch API calls when available
        results = []
        
        for request in requests:
            result = await self._process_single_request(request)
            results.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)
            
        return results
        
    def _build_prompt(self, request: SummarizationRequest) -> str:
        """Build the summarization prompt."""
        parts = [
            "Please provide a concise summary of the following content.",
            f"Maximum summary length: {request.max_tokens} tokens (approximately {request.max_tokens * 4} characters)."
        ]
        
        if request.preserve_code:
            parts.append("IMPORTANT: Preserve any code snippets or technical commands mentioned.")
            
        if request.preserve_decisions:
            parts.append("IMPORTANT: Preserve any decisions, conclusions, or action items.")
            
        if request.context:
            parts.append(f"\nContext: {request.context}")
            
        parts.extend([
            "\nContent to summarize:",
            "---",
            request.content,
            "---",
            "\nProvide only the summary, no additional commentary:"
        ])
        
        return "\n".join(parts)
        
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        # GPT-4o-mini pricing (as of late 2024)
        # $0.15 per 1M input tokens
        # $0.60 per 1M output tokens
        input_cost = (input_tokens / 1_000_000) * 0.15
        output_cost = (output_tokens / 1_000_000) * 0.60
        return input_cost + output_cost
        
    def _create_mock_summary(self, request: SummarizationRequest) -> SummarizationResult:
        """Create a mock summary for testing without LLM."""
        # Simple truncation for mock
        words = request.content.split()
        summary_words = words[:request.max_tokens // 2]  # Rough estimate
        summary = " ".join(summary_words)
        
        if len(summary) > request.max_tokens * 4:
            summary = summary[:request.max_tokens * 4] + "..."
            
        return SummarizationResult(
            request_id=request.id,
            summary=f"[Summary] {summary}",
            token_count=len(summary) // 4,
            quality_score=0.8,
            cost=0.0,
            duration_ms=10.0
        )
        
    def clear_cache(self):
        """Clear the summary cache."""
        self._cache.clear()
        logger.info("Cleared summary cache")
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of service metrics."""
        return {
            "total_requests": self.metrics.total_requests,
            "total_cost": round(self.metrics.total_cost, 4),
            "cache_hit_rate": round(self.metrics.get_cache_hit_rate(), 2),
            "avg_tokens_per_summary": (
                self.metrics.total_tokens_generated / self.metrics.total_requests 
                if self.metrics.total_requests > 0 else 0
            ),
            "errors": self.metrics.errors
        }
        
    async def estimate_cost_for_nodes(self, 
                                    node_count: int,
                                    avg_content_length: int,
                                    max_tokens: int = 100) -> float:
        """
        Estimate the cost of summarizing a given number of nodes.
        
        Args:
            node_count: Number of nodes to summarize
            avg_content_length: Average content length in characters
            max_tokens: Maximum tokens per summary
            
        Returns:
            Estimated cost in USD
        """
        avg_input_tokens = avg_content_length // 4
        avg_output_tokens = max_tokens
        
        total_input_tokens = node_count * avg_input_tokens
        total_output_tokens = node_count * avg_output_tokens
        
        return self._calculate_cost(total_input_tokens, total_output_tokens)