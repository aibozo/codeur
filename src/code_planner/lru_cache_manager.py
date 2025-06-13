"""
Enhanced cache manager with LRU eviction policy and memory limits.

This module extends the basic cache manager to add memory management
features including LRU eviction and size tracking.
"""

import json
import pickle
import hashlib
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import redis
from redis.exceptions import ConnectionError, TimeoutError

from src.core.logging import get_logger
from src.core.settings import get_settings

logger = get_logger(__name__)


class MemoryTracker:
    """Track memory usage of cached items."""
    
    def __init__(self, max_memory_mb: int = 1024):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_bytes = 0
        self.item_sizes = {}
        self.lock = threading.Lock()
    
    def add_item(self, key: str, data: Any) -> int:
        """Add item and track its size."""
        size = self._get_size(data)
        
        with self.lock:
            self.item_sizes[key] = size
            self.current_bytes += size
        
        return size
    
    def remove_item(self, key: str):
        """Remove item and update size tracking."""
        with self.lock:
            if key in self.item_sizes:
                self.current_bytes -= self.item_sizes[key]
                del self.item_sizes[key]
    
    def get_usage_percent(self) -> float:
        """Get memory usage as percentage of max."""
        return (self.current_bytes / self.max_memory_bytes) * 100
    
    def needs_eviction(self) -> bool:
        """Check if eviction is needed."""
        return self.current_bytes > self.max_memory_bytes
    
    @staticmethod
    def _get_size(obj: Any) -> int:
        """Estimate size of object in bytes."""
        if isinstance(obj, (str, bytes)):
            return len(obj)
        elif isinstance(obj, dict):
            # Estimate for dicts
            return sum(MemoryTracker._get_size(k) + MemoryTracker._get_size(v) 
                      for k, v in obj.items())
        elif isinstance(obj, (list, tuple)):
            return sum(MemoryTracker._get_size(item) for item in obj)
        else:
            # Fallback to pickling for size estimate
            try:
                return len(pickle.dumps(obj))
            except:
                return sys.getsizeof(obj)


class LRUCacheManager:
    """Enhanced cache manager with LRU eviction and memory management."""
    
    def __init__(self, redis_url: Optional[str] = None, 
                 db: int = 0, ttl_seconds: int = 3600,
                 max_memory_mb: int = 1024, max_items: int = 10000):
        """
        Initialize LRU cache manager.
        
        Args:
            redis_url: Redis connection URL (None for in-memory)
            db: Redis database number
            ttl_seconds: Time-to-live for cache entries
            max_memory_mb: Maximum memory usage in MB
            max_items: Maximum number of items
        """
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.cache.redis_url
        self.db = db
        self.ttl = ttl_seconds
        self.max_items = max_items
        self.client = None
        self.connected = False
        
        # Memory tracking
        self.memory_tracker = MemoryTracker(max_memory_mb)
        
        # LRU tracking for Redis
        self.access_times_key = "codeplanner:lru:access_times"
        
        # Try to connect to Redis
        if self.settings.cache.cache_backend == "redis":
            self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.from_url(self.redis_url, db=self.db, decode_responses=False)
            self.client.ping()
            self.connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            
            # Start LRU eviction thread
            if self.settings.cache.enable_lru_eviction:
                self._start_lru_thread()
                
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
            self.connected = False
    
    def _start_lru_thread(self):
        """Start background thread for LRU eviction."""
        def lru_worker():
            while self.connected:
                try:
                    self._perform_lru_eviction()
                    time.sleep(self.settings.cache.lru_check_interval_seconds)
                except Exception as e:
                    logger.error(f"LRU eviction error: {e}")
        
        thread = threading.Thread(target=lru_worker, daemon=True)
        thread.start()
    
    def _perform_lru_eviction(self):
        """Perform LRU eviction if needed."""
        if not self.connected:
            return
        
        try:
            # Get cache stats
            stats = self.get_cache_stats()
            total_keys = stats.get('codeplanner_keys', 0)
            
            # Check if eviction is needed
            if total_keys <= self.max_items:
                return
            
            # Get all codeplanner keys with access times
            pattern = "codeplanner:*"
            keys_to_check = []
            
            for key in self.client.scan_iter(match=pattern, count=100):
                if key.decode() not in [self.access_times_key]:
                    keys_to_check.append(key)
            
            # Get access times
            access_times = []
            for key in keys_to_check:
                score = self.client.zscore(self.access_times_key, key)
                if score is None:
                    # No access time recorded, use current time
                    score = time.time()
                access_times.append((key, score))
            
            # Sort by access time (oldest first)
            access_times.sort(key=lambda x: x[1])
            
            # Evict oldest entries
            evict_count = total_keys - int(self.max_items * 0.9)  # Evict to 90% capacity
            evicted = 0
            
            for key, _ in access_times[:evict_count]:
                self.client.delete(key)
                self.client.zrem(self.access_times_key, key)
                evicted += 1
            
            if evicted > 0:
                logger.info(f"LRU eviction: removed {evicted} entries")
                
        except Exception as e:
            logger.error(f"Error during LRU eviction: {e}")
    
    def _update_access_time(self, key: str):
        """Update access time for LRU tracking."""
        if self.connected and self.settings.cache.enable_lru_eviction:
            try:
                self.client.zadd(self.access_times_key, {key: time.time()})
            except:
                pass
    
    def _get_file_hash(self, file_path: str, content: Optional[str] = None) -> str:
        """Get hash of file content for cache key."""
        if content is None:
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
            except Exception:
                return ""
        
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        return hashlib.sha256(content).hexdigest()
    
    def _make_cache_key(self, prefix: str, file_path: str, file_hash: str) -> str:
        """Create cache key."""
        path = Path(file_path).as_posix()
        return f"codeplanner:{prefix}:{path}:{file_hash}"
    
    def get_file_analysis(self, file_path: str, file_content: Optional[str] = None) -> Optional[Dict]:
        """Get cached file analysis with LRU tracking."""
        if not self.connected:
            return None
        
        try:
            file_hash = self._get_file_hash(file_path, file_content)
            key = self._make_cache_key("ast", file_path, file_hash)
            
            data = self.client.get(key)
            if data:
                # Update access time
                self._update_access_time(key)
                return pickle.loads(data)
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def set_file_analysis(self, file_path: str, analysis: Dict, 
                         file_content: Optional[str] = None):
        """Cache file analysis with size tracking."""
        if not self.connected:
            return
        
        try:
            file_hash = self._get_file_hash(file_path, file_content)
            key = self._make_cache_key("ast", file_path, file_hash)
            
            # Serialize and check size
            data = pickle.dumps(analysis)
            
            # Store with TTL
            self.client.setex(key, self.ttl, data)
            
            # Update access time
            self._update_access_time(key)
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get enhanced cache statistics."""
        stats = {
            "connected": self.connected,
            "backend": "redis" if self.connected else "none",
            "ttl_seconds": self.ttl,
            "max_items": self.max_items,
            "lru_enabled": self.settings.cache.enable_lru_eviction,
        }
        
        if self.connected:
            try:
                info = self.client.info()
                codeplanner_keys = len(list(self.client.scan_iter(
                    match="codeplanner:*", count=100
                )))
                
                stats.update({
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "total_keys": self.client.dbsize(),
                    "codeplanner_keys": codeplanner_keys,
                    "eviction_policy": info.get("maxmemory_policy", "N/A"),
                })
            except Exception as e:
                stats["error"] = str(e)
        
        return stats
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
            self.connected = False


class InMemoryLRUCache(LRUCacheManager):
    """In-memory LRU cache implementation."""
    
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 10000,
                 max_memory_mb: int = 1024):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self.memory_tracker = MemoryTracker(max_memory_mb)
        
        # Use OrderedDict for LRU behavior
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
        self.connected = True
        
        logger.info("Using in-memory LRU cache")
        
        # Start eviction thread
        self._start_eviction_thread()
    
    def _start_eviction_thread(self):
        """Start background thread for periodic eviction."""
        settings = get_settings()
        
        def eviction_worker():
            while True:
                try:
                    self._perform_eviction()
                    time.sleep(settings.cache.lru_check_interval_seconds)
                except Exception as e:
                    logger.error(f"Eviction error: {e}")
        
        thread = threading.Thread(target=eviction_worker, daemon=True)
        thread.start()
    
    def _perform_eviction(self):
        """Perform TTL and LRU eviction."""
        with self.lock:
            # Remove expired entries
            now = datetime.now()
            expired = []
            
            for key, timestamp in list(self.timestamps.items()):
                if now - timestamp > timedelta(seconds=self.ttl):
                    expired.append(key)
            
            for key in expired:
                self._remove_item(key)
            
            # LRU eviction if over capacity
            while len(self.cache) > self.max_items:
                # Remove least recently used (first item)
                key, _ = self.cache.popitem(last=False)
                self._remove_item(key)
            
            # Memory-based eviction
            while self.memory_tracker.needs_eviction() and self.cache:
                key, _ = self.cache.popitem(last=False)
                self._remove_item(key)
    
    def _remove_item(self, key: str):
        """Remove item from cache and update tracking."""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
        self.memory_tracker.remove_item(key)
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.timestamps:
            return True
        
        age = datetime.now() - self.timestamps[key]
        return age > timedelta(seconds=self.ttl)
    
    def get_file_analysis(self, file_path: str, file_content: Optional[str] = None) -> Optional[Dict]:
        """Get cached file analysis."""
        file_hash = self._get_file_hash(file_path, file_content)
        key = self._make_cache_key("ast", file_path, file_hash)
        
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
        
        return None
    
    def set_file_analysis(self, file_path: str, analysis: Dict, 
                         file_content: Optional[str] = None):
        """Cache file analysis."""
        file_hash = self._get_file_hash(file_path, file_content)
        key = self._make_cache_key("ast", file_path, file_hash)
        
        with self.lock:
            # Add to cache (moves to end if exists)
            self.cache[key] = analysis
            self.cache.move_to_end(key)
            self.timestamps[key] = datetime.now()
            
            # Track memory
            self.memory_tracker.add_item(key, analysis)
            
            # Trigger eviction if needed
            self._perform_eviction()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "connected": True,
                "backend": "memory",
                "total_keys": len(self.cache),
                "max_items": self.max_items,
                "memory_usage_percent": self.memory_tracker.get_usage_percent(),
                "memory_usage_mb": self.memory_tracker.current_bytes / (1024 * 1024),
                "ttl_seconds": self.ttl
            }
    
    def close(self):
        """No-op for in-memory cache."""
        pass


def create_lru_cache_manager(**kwargs) -> LRUCacheManager:
    """
    Create appropriate LRU cache manager based on settings.
    
    Returns:
        LRUCacheManager instance (Redis-based or in-memory)
    """
    settings = get_settings()
    
    if settings.cache.cache_backend == "redis":
        try:
            manager = LRUCacheManager(
                redis_url=settings.cache.redis_url,
                db=settings.cache.redis_db,
                ttl_seconds=settings.cache.cache_ttl_seconds,
                max_memory_mb=settings.cache.max_memory_cache_mb,
                max_items=settings.cache.max_memory_cache_items,
                **kwargs
            )
            if manager.connected:
                return manager
        except Exception as e:
            logger.warning(f"Failed to create Redis cache: {e}")
    
    # Fallback to in-memory
    return InMemoryLRUCache(
        ttl_seconds=settings.cache.cache_ttl_seconds,
        max_items=settings.cache.max_memory_cache_items,
        max_memory_mb=settings.cache.max_memory_cache_mb,
        **kwargs
    )