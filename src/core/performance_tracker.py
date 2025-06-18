"""
Simple performance tracker for debugging slow operations.

This module provides decorators and context managers to track execution times
and identify hot loops in the codebase.
"""

import time
import functools
import asyncio
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track performance metrics for different operations."""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.active_timers: Dict[str, float] = {}
        self.enabled = True
        
    def start_timing(self, operation: str) -> float:
        """Start timing an operation."""
        if not self.enabled:
            return 0
        start_time = time.time()
        self.active_timers[operation] = start_time
        return start_time
        
    def end_timing(self, operation: str) -> float:
        """End timing and record the duration."""
        if not self.enabled or operation not in self.active_timers:
            return 0
            
        start_time = self.active_timers.pop(operation)
        duration = time.time() - start_time
        self.timings[operation].append(duration)
        self.call_counts[operation] += 1
        
        # Log if operation took more than 5 seconds
        if duration > 5.0:
            logger.warning(f"SLOW OPERATION: {operation} took {duration:.2f}s")
            
        return duration
        
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        for operation, times in self.timings.items():
            if times:
                stats[operation] = {
                    "count": self.call_counts[operation],
                    "total": sum(times),
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "last": times[-1] if times else 0
                }
        return stats
        
    def log_stats(self, prefix: str = ""):
        """Log current performance stats."""
        stats = self.get_stats()
        if not stats:
            return
            
        logger.info(f"{prefix}Performance Statistics:")
        logger.info("=" * 60)
        
        # Sort by total time descending
        sorted_ops = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)
        
        for operation, data in sorted_ops:
            logger.info(
                f"{operation}: "
                f"count={data['count']}, "
                f"total={data['total']:.2f}s, "
                f"avg={data['avg']:.2f}s, "
                f"max={data['max']:.2f}s"
            )
            
    def clear(self):
        """Clear all timings."""
        self.timings.clear()
        self.call_counts.clear()
        self.active_timers.clear()


# Global tracker instance
_global_tracker = PerformanceTracker()


def track_time(operation: str = None):
    """Decorator to track function execution time."""
    def decorator(func):
        op_name = operation or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                _global_tracker.start_timing(op_name)
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = _global_tracker.end_timing(op_name)
                    if duration > 10.0:  # Log extra info for very slow operations
                        logger.warning(
                            f"VERY SLOW: {op_name} took {duration:.2f}s "
                            f"(args={args[:2] if args else 'none'})"
                        )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                _global_tracker.start_timing(op_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    _global_tracker.end_timing(op_name)
            return sync_wrapper
    return decorator


@asynccontextmanager
async def track_async_operation(operation: str):
    """Async context manager to track operation time."""
    _global_tracker.start_timing(operation)
    try:
        yield
    finally:
        _global_tracker.end_timing(operation)


@contextmanager
def track_operation(operation: str):
    """Context manager to track operation time."""
    _global_tracker.start_timing(operation)
    try:
        yield
    finally:
        _global_tracker.end_timing(operation)


def get_tracker() -> PerformanceTracker:
    """Get the global performance tracker."""
    return _global_tracker


def log_performance_stats(prefix: str = ""):
    """Log current performance statistics."""
    _global_tracker.log_stats(prefix)


def reset_tracker():
    """Reset the global tracker."""
    _global_tracker.clear()


# Specific trackers for different components
class APICallTracker:
    """Track API calls specifically."""
    
    def __init__(self):
        self.api_calls: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
    def track_call(self, api_name: str, duration: float, tokens: int = 0, **kwargs):
        """Track an API call."""
        self.api_calls[api_name].append({
            "timestamp": datetime.now(),
            "duration": duration,
            "tokens": tokens,
            **kwargs
        })
        
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API call statistics."""
        stats = {}
        for api_name, calls in self.api_calls.items():
            durations = [c["duration"] for c in calls]
            tokens = [c["tokens"] for c in calls]
            stats[api_name] = {
                "count": len(calls),
                "total_time": sum(durations),
                "avg_time": sum(durations) / len(durations) if durations else 0,
                "total_tokens": sum(tokens),
                "avg_tokens": sum(tokens) / len(tokens) if tokens else 0
            }
        return stats


# Global API tracker
_api_tracker = APICallTracker()


def track_api_call(api_name: str, duration: float, **kwargs):
    """Track an API call."""
    _api_tracker.track_call(api_name, duration, **kwargs)


def get_api_stats() -> Dict[str, Any]:
    """Get API call statistics."""
    return _api_tracker.get_api_stats()