"""
Redis-based caching for AST analysis and call graphs.

This module provides persistent caching using Redis to speed up
repeated analysis of the same files.
"""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis
from redis.exceptions import ConnectionError, TimeoutError


class CacheManager:
    """Manages Redis-based caching for Code Planner."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 db: int = 0, ttl_seconds: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL
            db: Redis database number
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.redis_url = redis_url
        self.db = db
        self.ttl = ttl_seconds
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.from_url(self.redis_url, db=self.db, decode_responses=False)
            # Test connection
            self.client.ping()
            self.connected = True
            print(f"Connected to Redis at {self.redis_url}")
        except (ConnectionError, TimeoutError) as e:
            print(f"Failed to connect to Redis: {e}")
            self.connected = False
    
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
        # Normalize path
        path = Path(file_path).as_posix()
        return f"codeplanner:{prefix}:{path}:{file_hash}"
    
    def get_file_analysis(self, file_path: str, file_content: Optional[str] = None) -> Optional[Dict]:
        """Get cached file analysis."""
        if not self.connected:
            return None
        
        try:
            file_hash = self._get_file_hash(file_path, file_content)
            key = self._make_cache_key("ast", file_path, file_hash)
            
            data = self.client.get(key)
            if data:
                # Deserialize
                return pickle.loads(data)
            
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    def set_file_analysis(self, file_path: str, analysis: Dict, 
                         file_content: Optional[str] = None):
        """Cache file analysis."""
        if not self.connected:
            return
        
        try:
            file_hash = self._get_file_hash(file_path, file_content)
            key = self._make_cache_key("ast", file_path, file_hash)
            
            # Serialize and store
            data = pickle.dumps(analysis)
            self.client.setex(key, self.ttl, data)
            
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def get_call_graph(self, repo_path: str, file_list_hash: str) -> Optional[Any]:
        """Get cached call graph."""
        if not self.connected:
            return None
        
        try:
            key = self._make_cache_key("callgraph", repo_path, file_list_hash)
            data = self.client.get(key)
            
            if data:
                return pickle.loads(data)
                
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    def set_call_graph(self, repo_path: str, file_list_hash: str, graph_data: Any):
        """Cache call graph."""
        if not self.connected:
            return
        
        try:
            key = self._make_cache_key("callgraph", repo_path, file_list_hash)
            data = pickle.dumps(graph_data)
            self.client.setex(key, self.ttl, data)
            
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def get_complexity_metrics(self, repo_path: str) -> Optional[Dict]:
        """Get cached complexity metrics."""
        if not self.connected:
            return None
        
        try:
            key = f"codeplanner:metrics:{repo_path}"
            data = self.client.get(key)
            
            if data:
                return json.loads(data)
                
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    def set_complexity_metrics(self, repo_path: str, metrics: Dict):
        """Cache complexity metrics."""
        if not self.connected:
            return
        
        try:
            key = f"codeplanner:metrics:{repo_path}"
            data = json.dumps(metrics)
            self.client.setex(key, self.ttl // 2, data)  # Shorter TTL for metrics
            
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def invalidate_file(self, file_path: str):
        """Invalidate all cache entries for a file."""
        if not self.connected:
            return
        
        try:
            # Find and delete all keys for this file
            pattern = f"codeplanner:ast:{file_path}:*"
            for key in self.client.scan_iter(match=pattern):
                self.client.delete(key)
                
        except Exception as e:
            print(f"Cache invalidate error: {e}")
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern."""
        if not self.connected:
            return
        
        try:
            if pattern:
                search_pattern = f"codeplanner:{pattern}"
            else:
                search_pattern = "codeplanner:*"
            
            deleted = 0
            for key in self.client.scan_iter(match=search_pattern):
                self.client.delete(key)
                deleted += 1
            
            print(f"Cleared {deleted} cache entries")
            
        except Exception as e:
            print(f"Cache clear error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "connected": self.connected,
            "redis_url": self.redis_url,
            "db": self.db,
            "ttl_seconds": self.ttl
        }
        
        if self.connected:
            try:
                info = self.client.info()
                stats.update({
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "total_keys": self.client.dbsize(),
                    "codeplanner_keys": len(list(self.client.scan_iter(match="codeplanner:*", count=100)))
                })
            except Exception as e:
                stats["error"] = str(e)
        
        return stats
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
            self.connected = False


class InMemoryCacheManager(CacheManager):
    """In-memory fallback when Redis is not available."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}
        self.connected = True
        print("Using in-memory cache (Redis not available)")
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.timestamps:
            return True
        
        age = datetime.now() - self.timestamps[key]
        return age > timedelta(seconds=self.ttl)
    
    def _clean_expired(self):
        """Remove expired entries."""
        expired = [k for k in self.cache if self._is_expired(k)]
        for k in expired:
            del self.cache[k]
            del self.timestamps[k]
    
    def get_file_analysis(self, file_path: str, file_content: Optional[str] = None) -> Optional[Dict]:
        """Get cached file analysis."""
        self._clean_expired()
        
        file_hash = self._get_file_hash(file_path, file_content)
        key = self._make_cache_key("ast", file_path, file_hash)
        
        if key in self.cache and not self._is_expired(key):
            return self.cache[key]
        
        return None
    
    def set_file_analysis(self, file_path: str, analysis: Dict, 
                         file_content: Optional[str] = None):
        """Cache file analysis."""
        file_hash = self._get_file_hash(file_path, file_content)
        key = self._make_cache_key("ast", file_path, file_hash)
        
        self.cache[key] = analysis
        self.timestamps[key] = datetime.now()
        
        # Limit cache size
        if len(self.cache) > 1000:
            self._clean_expired()
            # Remove oldest entries if still too large
            if len(self.cache) > 1000:
                oldest = sorted(self.timestamps.items(), key=lambda x: x[1])[:200]
                for k, _ in oldest:
                    del self.cache[k]
                    del self.timestamps[k]
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries."""
        if pattern:
            keys_to_delete = [k for k in self.cache if pattern in k]
            for k in keys_to_delete:
                del self.cache[k]
                if k in self.timestamps:
                    del self.timestamps[k]
        else:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._clean_expired()
        return {
            "connected": True,
            "type": "in-memory",
            "total_keys": len(self.cache),
            "ttl_seconds": self.ttl
        }
    
    def close(self):
        """No-op for in-memory cache."""
        pass


def create_cache_manager(redis_url: Optional[str] = None, **kwargs) -> CacheManager:
    """
    Create appropriate cache manager based on Redis availability.
    
    Args:
        redis_url: Redis URL, if None will try localhost
        **kwargs: Additional arguments for CacheManager
        
    Returns:
        CacheManager instance (Redis-based or in-memory fallback)
    """
    if redis_url is None:
        redis_url = "redis://localhost:6379"
    
    # Try Redis first
    try:
        manager = CacheManager(redis_url, **kwargs)
        if manager.connected:
            return manager
    except Exception:
        pass
    
    # Fallback to in-memory
    return InMemoryCacheManager(ttl_seconds=kwargs.get('ttl_seconds', 3600))