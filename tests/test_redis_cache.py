#!/usr/bin/env python3
"""
Test Redis caching functionality.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner.cache_manager import create_cache_manager, CacheManager, InMemoryCacheManager
from src.code_planner.ast_analyzer_v2 import EnhancedASTAnalyzer


def test_cache_manager():
    """Test cache manager functionality."""
    print("🔴 Testing Cache Manager")
    print("=" * 50)
    
    # Create cache manager (will use Redis if available, in-memory otherwise)
    cache = create_cache_manager()
    
    # Check what type we got
    if isinstance(cache, InMemoryCacheManager):
        print("📦 Using in-memory cache (Redis not available)")
    else:
        print("📦 Using Redis cache")
    
    # Test basic operations
    test_data = {
        "path": "test.py",
        "language": "python",
        "symbols": [
            {"name": "test_func", "kind": "function", "complexity": 3}
        ],
        "imports": ["os", "sys"],
        "exports": ["test_func"],
        "dependencies": ["os", "sys"],
        "complexity": 3
    }
    
    # Set and get
    cache.set_file_analysis("test.py", test_data)
    retrieved = cache.get_file_analysis("test.py")
    
    assert retrieved is not None, "Failed to retrieve cached data"
    assert retrieved["path"] == "test.py", "Cached data mismatch"
    print("✓ Basic cache operations working")
    
    # Test cache stats
    stats = cache.get_cache_stats()
    print(f"\n📊 Cache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test cache invalidation
    cache.invalidate_file("test.py")
    retrieved = cache.get_file_analysis("test.py")
    assert retrieved is None, "Cache invalidation failed"
    print("\n✓ Cache invalidation working")
    
    # Cleanup
    cache.clear_cache()
    cache.close()
    
    return True


def test_analyzer_with_caching():
    """Test analyzer with caching enabled."""
    print("\n🧪 Testing Analyzer with Caching")
    print("=" * 50)
    
    # Create test repository
    test_repo = Path("test_cache_repo")
    test_repo.mkdir(exist_ok=True)
    
    # Create test file
    test_file = test_repo / "cached_test.py"
    test_file.write_text("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

class MathHelper:
    @staticmethod
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
        return True
""")
    
    # Create analyzer with caching
    analyzer = EnhancedASTAnalyzer(str(test_repo))
    
    # First analysis (cache miss)
    start_time = time.time()
    analysis1 = analyzer.analyze_file("cached_test.py")
    first_time = time.time() - start_time
    
    assert analysis1 is not None, "Analysis failed"
    assert len(analysis1.symbols) == 4, f"Expected 4 symbols, got {len(analysis1.symbols)}"
    print(f"✓ First analysis completed in {first_time:.3f}s (cache miss)")
    
    # Clear in-memory cache to force Redis lookup
    analyzer._symbol_cache.clear()
    
    # Second analysis (should be cached)
    start_time = time.time()
    analysis2 = analyzer.analyze_file("cached_test.py")
    cached_time = time.time() - start_time
    
    assert analysis2 is not None, "Cached analysis failed"
    assert len(analysis2.symbols) == 4, "Cached data mismatch"
    print(f"✓ Cached analysis completed in {cached_time:.3f}s")
    
    # Verify speedup (cached should be faster, but only if using Redis)
    if not isinstance(analyzer.cache, InMemoryCacheManager):
        assert cached_time < first_time, "Cache didn't improve performance"
        print(f"✓ Cache speedup: {first_time/cached_time:.1f}x faster")
    
    # Test cache metrics in analyzer info
    info = analyzer.get_analyzer_info()
    print(f"\n📊 Analyzer Info:")
    print(f"  Tree-sitter: {info['tree_sitter_available']}")
    print(f"  Languages: {info.get('tree_sitter_languages', [])}")
    print(f"  Cache type: {info['cache_stats'].get('type', 'redis')}")
    print(f"  Cache keys: {info['cache_stats'].get('total_keys', 'N/A')}")
    
    # Test call graph metrics
    analyzer.build_call_graph(["cached_test.py"])
    metrics = analyzer.get_call_graph_metrics()
    print(f"\n📈 Call Graph Metrics:")
    print(f"  Nodes: {metrics['total_nodes']}")
    print(f"  Edges: {metrics['total_edges']}")
    print(f"  Most complex: {metrics['most_complex_functions'][0] if metrics['most_complex_functions'] else 'N/A'}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_repo, ignore_errors=True)
    analyzer.cache.clear_cache("ast:*cached_test*")
    
    return True


def test_cache_expiration():
    """Test cache TTL functionality."""
    print("\n⏰ Testing Cache Expiration")
    print("=" * 50)
    
    # Create cache with short TTL
    cache = create_cache_manager(ttl_seconds=2)
    
    # Set data
    test_data = {"test": "data"}
    cache.set_file_analysis("expire_test.py", test_data)
    
    # Verify it's there
    retrieved = cache.get_file_analysis("expire_test.py")
    assert retrieved is not None, "Data not cached"
    print("✓ Data cached successfully")
    
    if isinstance(cache, InMemoryCacheManager):
        # Test in-memory expiration
        print("  Waiting for in-memory expiration...")
        time.sleep(3)
        
        retrieved = cache.get_file_analysis("expire_test.py")
        assert retrieved is None, "Data didn't expire"
        print("✓ In-memory cache expiration working")
    else:
        print("  (Redis expiration handled by Redis TTL)")
    
    cache.close()
    return True


if __name__ == "__main__":
    print("\n🚀 Redis Cache Test Suite\n")
    
    success = True
    success &= test_cache_manager()
    success &= test_analyzer_with_caching()
    success &= test_cache_expiration()
    
    if success:
        print("\n✅ All cache tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(0 if success else 1)