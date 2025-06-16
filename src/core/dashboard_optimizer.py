"""
Dashboard performance optimization utilities.

This module provides caching, debouncing, and data reduction
strategies to optimize dashboard performance.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
from collections import OrderedDict

from src.core.logging import get_logger

logger = get_logger(__name__)


class DashboardCache:
    """
    LRU cache for dashboard data with TTL support.
    
    Reduces redundant API calls and improves response times.
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.utcnow() < entry['expires']:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    return entry['value']
                else:
                    # Expired
                    del self.cache[key]
        return None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires = datetime.utcnow() + timedelta(seconds=ttl)
        
        async with self._lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self.cache.popitem(last=False)
            
            self.cache[key] = {
                'value': value,
                'expires': expires
            }
            self.cache.move_to_end(key)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()


class DataAggregator:
    """
    Aggregates and reduces data for efficient transmission.
    
    Implements strategies to reduce data size while maintaining
    visualization quality.
    """
    
    @staticmethod
    def downsample_timeseries(data: List[Dict[str, Any]], max_points: int = 200) -> List[Dict[str, Any]]:
        """
        Downsample time series data using LTTB algorithm.
        
        Args:
            data: Time series data points
            max_points: Maximum number of points to return
            
        Returns:
            Downsampled data
        """
        if len(data) <= max_points:
            return data
            
        # Simple decimation for now (TODO: implement LTTB)
        step = len(data) / max_points
        indices = [int(i * step) for i in range(max_points)]
        return [data[i] for i in indices if i < len(data)]
    
    @staticmethod
    def aggregate_logs(logs: List[Dict[str, Any]], max_logs: int = 100) -> Dict[str, Any]:
        """
        Aggregate logs with summary statistics.
        
        Args:
            logs: Log entries
            max_logs: Maximum logs to return
            
        Returns:
            Aggregated log data with statistics
        """
        # Count by level
        level_counts = {}
        for log in logs:
            level = log.get('level', 'INFO')
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # Get recent logs
        recent_logs = logs[-max_logs:] if len(logs) > max_logs else logs
        
        return {
            'logs': recent_logs,
            'total_count': len(logs),
            'level_counts': level_counts,
            'truncated': len(logs) > max_logs
        }
    
    @staticmethod
    def optimize_graph_data(graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize graph data for transmission.
        
        Args:
            graph_data: Full graph data
            
        Returns:
            Optimized graph data
        """
        # Remove unnecessary fields
        optimized = {
            'nodes': [],
            'edges': [],
            'timestamp': graph_data.get('timestamp'),
            'stats': graph_data.get('stats', {})
        }
        
        # Optimize nodes
        for node in graph_data.get('nodes', []):
            optimized['nodes'].append({
                'id': node['id'],
                'label': node['label'],
                'type': node['type'],
                'x': round(node['x'], 1),
                'y': round(node['y'], 1),
                'color': node['color'],
                'icon': node['icon']
            })
        
        # Optimize edges (only include active ones and essential data)
        for edge in graph_data.get('edges', []):
            if edge.get('active') or edge.get('flow', 0) > 0:
                optimized['edges'].append({
                    'id': edge['id'],
                    'source': edge['source'],
                    'target': edge['target'],
                    'type': edge['type'],
                    'active': edge.get('active', False),
                    'flow': round(edge.get('flow', 0), 2)
                })
        
        return optimized


class UpdateDebouncer:
    """
    Debounces rapid updates to prevent overwhelming the frontend.
    """
    
    def __init__(self, delay: float = 0.1):
        """
        Initialize debouncer.
        
        Args:
            delay: Delay in seconds before executing
        """
        self.delay = delay
        self._tasks: Dict[str, asyncio.Task] = {}
        
    async def debounce(self, key: str, coro: Callable[[], Any]) -> None:
        """
        Debounce a coroutine execution.
        
        Args:
            key: Unique key for this operation
            coro: Coroutine to execute
        """
        # Cancel existing task if any
        if key in self._tasks:
            self._tasks[key].cancel()
        
        # Create new task with delay
        async def delayed_execution():
            await asyncio.sleep(self.delay)
            try:
                await coro()
            finally:
                self._tasks.pop(key, None)
        
        self._tasks[key] = asyncio.create_task(delayed_execution())


class MetricsBuffer:
    """
    Buffers metrics updates to reduce frequency of broadcasts.
    """
    
    def __init__(self, flush_interval: float = 1.0, max_buffer_size: int = 100):
        """
        Initialize metrics buffer.
        
        Args:
            flush_interval: Interval to flush buffer in seconds
            max_buffer_size: Maximum buffer size before forced flush
        """
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size
        self.buffer: Dict[str, List[Dict[str, Any]]] = {}
        self._flush_task = None
        self._lock = asyncio.Lock()
        self._flush_callback = None
        
    async def start(self, flush_callback: Callable[[Dict[str, List]], Any]):
        """
        Start the buffer with flush callback.
        
        Args:
            flush_callback: Callback to handle flushed data
        """
        self._flush_callback = flush_callback
        self._flush_task = asyncio.create_task(self._flush_loop())
        
    async def stop(self):
        """Stop the buffer and flush remaining data."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush()
        
    async def add(self, metric_type: str, data: Dict[str, Any]) -> None:
        """
        Add data to buffer.
        
        Args:
            metric_type: Type of metric
            data: Metric data
        """
        async with self._lock:
            if metric_type not in self.buffer:
                self.buffer[metric_type] = []
            
            self.buffer[metric_type].append({
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            })
            
            # Force flush if buffer is full
            if len(self.buffer[metric_type]) >= self.max_buffer_size:
                await self._flush()
    
    async def _flush(self) -> None:
        """Flush buffer to callback."""
        async with self._lock:
            if not self.buffer or not self._flush_callback:
                return
                
            # Get buffer contents
            to_flush = self.buffer
            self.buffer = {}
        
        # Call flush callback
        try:
            await self._flush_callback(to_flush)
        except Exception as e:
            logger.error(f"Error in flush callback: {e}")
    
    async def _flush_loop(self) -> None:
        """Periodic flush loop."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")


def cached_endpoint(ttl: int = 60):
    """
    Decorator for caching API endpoint responses.
    
    Args:
        ttl: Time to live in seconds
    """
    def decorator(func):
        cache = DashboardCache(max_size=50, default_ttl=ttl)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {
                'func': func.__name__,
                'args': str(args),
                'kwargs': str(sorted(kwargs.items()))
            }
            key = hashlib.md5(json.dumps(key_data).encode()).hexdigest()
            
            # Check cache
            cached = await cache.get(key)
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(key, result, ttl)
            
            return result
        
        # Attach cache for manual control
        wrapper.cache = cache
        return wrapper
    
    return decorator


# Optimization utilities
class DashboardOptimizer:
    """
    Central optimizer for dashboard performance.
    """
    
    def __init__(self):
        self.cache = DashboardCache()
        self.aggregator = DataAggregator()
        self.debouncer = UpdateDebouncer()
        self.metrics_buffer = MetricsBuffer()
        
    async def start(self, broadcast_callback):
        """Start optimizer services."""
        await self.metrics_buffer.start(broadcast_callback)
        
    async def stop(self):
        """Stop optimizer services."""
        await self.metrics_buffer.stop()
        await self.cache.clear()