"""
Resilient LLM client wrapper with advanced retry logic and error handling.

This module provides a resilient wrapper around the LLM client with:
- Configurable retry strategies
- Circuit breaker pattern
- Rate limiting
- Error categorization and handling
- Fallback mechanisms
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_random_exponential,
    retry_if_exception_type,
    before_retry,
    after_retry
)
from openai import (
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    AuthenticationError,
    BadRequestError
)

from src.llm import LLMClient

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for different handling strategies."""
    TRANSIENT = "transient"  # Temporary errors that should be retried
    RATE_LIMIT = "rate_limit"  # Rate limit errors requiring backoff
    CLIENT = "client"  # Client errors that should not be retried
    AUTH = "auth"  # Authentication errors
    UNKNOWN = "unknown"  # Unknown errors


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Simple circuit breaker implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker logic."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int = 10, per: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
    
    def allow_request(self) -> bool:
        """Check if request is allowed."""
        current = time.time()
        time_passed = current - self.last_check
        self.last_check = current
        self.allowance += time_passed * (self.rate / self.per)
        
        if self.allowance > self.rate:
            self.allowance = self.rate
        
        if self.allowance < 1.0:
            return False
        
        self.allowance -= 1.0
        return True
    
    def time_until_reset(self) -> float:
        """Get time until next request is allowed."""
        if self.allowance >= 1.0:
            return 0.0
        return (1.0 - self.allowance) * (self.per / self.rate)


def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize an error for appropriate handling."""
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return ErrorCategory.TRANSIENT
    elif isinstance(error, RateLimitError):
        return ErrorCategory.RATE_LIMIT
    elif isinstance(error, AuthenticationError):
        return ErrorCategory.AUTH
    elif isinstance(error, BadRequestError):
        return ErrorCategory.CLIENT
    elif isinstance(error, APIError):
        # Check status code if available
        if hasattr(error, 'status_code'):
            if error.status_code >= 500:
                return ErrorCategory.TRANSIENT
            elif error.status_code == 429:
                return ErrorCategory.RATE_LIMIT
            elif error.status_code >= 400:
                return ErrorCategory.CLIENT
    return ErrorCategory.UNKNOWN


def log_retry_attempt(retry_state):
    """Log retry attempts."""
    logger.warning(
        f"Retrying LLM call (attempt {retry_state.attempt_number}): "
        f"{retry_state.outcome.exception()}"
    )


class ResilientLLMClient:
    """
    Resilient wrapper around LLM client with advanced error handling.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        max_retries: int = 5,
        max_retry_delay: int = 60,
        rate_limit: Optional[Dict[str, int]] = None,
        circuit_breaker_enabled: bool = True,
        fallback_model: Optional[str] = None
    ):
        """
        Initialize resilient LLM client.
        
        Args:
            model: Primary model to use
            max_retries: Maximum number of retry attempts
            max_retry_delay: Maximum delay between retries in seconds
            rate_limit: Rate limiting config (e.g., {"rate": 10, "per": 60})
            circuit_breaker_enabled: Whether to use circuit breaker
            fallback_model: Fallback model to use if primary fails
        """
        self.primary_client = LLMClient(model=model)
        self.fallback_client = LLMClient(model=fallback_model) if fallback_model else None
        self.max_retries = max_retries
        self.max_retry_delay = max_retry_delay
        
        # Initialize rate limiter
        if rate_limit:
            self.rate_limiter = RateLimiter(**rate_limit)
        else:
            self.rate_limiter = None
        
        # Initialize circuit breaker
        if circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=120,
                expected_exception=APIError
            )
        else:
            self.circuit_breaker = None
        
        # Track recent errors for analysis
        self.recent_errors = deque(maxlen=100)
        
        logger.info(
            f"Resilient LLM Client initialized with model: {self.primary_client.model}, "
            f"fallback: {fallback_model}"
        )
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        category = categorize_error(error)
        return category in [ErrorCategory.TRANSIENT, ErrorCategory.RATE_LIMIT]
    
    def _get_retry_decorator(self):
        """Get configured retry decorator."""
        return retry(
            stop=stop_after_attempt(self.max_retries) | stop_after_delay(self.max_retry_delay),
            wait=wait_random_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((APIError, APIConnectionError, APITimeoutError, RateLimitError)),
            before=before_retry(log_retry_attempt)
        )
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        if self.rate_limiter and not self.rate_limiter.allow_request():
            wait_time = self.rate_limiter.time_until_reset()
            logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)
    
    def _record_error(self, error: Exception):
        """Record error for analysis."""
        self.recent_errors.append({
            'timestamp': datetime.now(),
            'error_type': type(error).__name__,
            'category': categorize_error(error),
            'message': str(error)
        })
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
        use_fallback: bool = True,
        **kwargs
    ) -> str:
        """
        Generate text with resilient error handling.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            use_fallback: Whether to use fallback model on failure
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            Generated text
        """
        # Check rate limit
        self._check_rate_limit()
        
        # Define the actual generation function
        def _generate_with_client(client: LLMClient) -> str:
            if self.circuit_breaker:
                return self.circuit_breaker.call(
                    client.generate,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:
                return client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
        
        # Apply retry decorator
        retryable_generate = self._get_retry_decorator()(_generate_with_client)
        
        try:
            # Try with primary client
            return retryable_generate(self.primary_client)
        except Exception as e:
            self._record_error(e)
            
            # Check if we should use fallback
            if use_fallback and self.fallback_client and self._should_retry(e):
                logger.warning(f"Primary model failed, trying fallback: {e}")
                try:
                    return retryable_generate(self.fallback_client)
                except Exception as fallback_error:
                    self._record_error(fallback_error)
                    logger.error(f"Fallback model also failed: {fallback_error}")
                    raise
            else:
                raise
    
    def generate_with_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
        use_fallback: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate JSON response with resilient error handling.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            use_fallback: Whether to use fallback model on failure
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            Parsed JSON response
        """
        # Check rate limit
        self._check_rate_limit()
        
        # Define the actual generation function
        def _generate_json_with_client(client: LLMClient) -> Dict[str, Any]:
            if self.circuit_breaker:
                return self.circuit_breaker.call(
                    client.generate_with_json,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:
                return client.generate_with_json(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
        
        # Apply retry decorator
        retryable_generate = self._get_retry_decorator()(_generate_json_with_client)
        
        try:
            # Try with primary client
            return retryable_generate(self.primary_client)
        except Exception as e:
            self._record_error(e)
            
            # Check if we should use fallback
            if use_fallback and self.fallback_client and self._should_retry(e):
                logger.warning(f"Primary model failed, trying fallback: {e}")
                try:
                    return retryable_generate(self.fallback_client)
                except Exception as fallback_error:
                    self._record_error(fallback_error)
                    logger.error(f"Fallback model also failed: {fallback_error}")
                    raise
            else:
                raise
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        if not self.recent_errors:
            return {"total_errors": 0, "categories": {}}
        
        categories = {}
        for error in self.recent_errors:
            cat = error['category'].value
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        return {
            "total_errors": len(self.recent_errors),
            "categories": categories,
            "recent_errors": list(self.recent_errors)[-10:]  # Last 10 errors
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of LLM service."""
        health = {
            "primary_model": self.primary_client.model,
            "fallback_model": self.fallback_client.model if self.fallback_client else None,
            "circuit_breaker_state": self.circuit_breaker.state.value if self.circuit_breaker else "disabled",
            "error_summary": self.get_error_summary()
        }
        
        # Test primary model
        try:
            self.primary_client.generate("Test", max_tokens=10)
            health["primary_status"] = "healthy"
        except Exception as e:
            health["primary_status"] = f"unhealthy: {str(e)}"
        
        # Test fallback model if available
        if self.fallback_client:
            try:
                self.fallback_client.generate("Test", max_tokens=10)
                health["fallback_status"] = "healthy"
            except Exception as e:
                health["fallback_status"] = f"unhealthy: {str(e)}"
        
        return health