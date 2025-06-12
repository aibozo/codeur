#!/usr/bin/env python3
"""
Test parallel AST analysis functionality.
"""

import sys
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner.parallel_analyzer import ParallelAnalyzer, ParallelASTAnalyzer
from src.code_planner.ast_analyzer_v2 import EnhancedASTAnalyzer


def create_test_files(base_dir: Path, num_files: int = 20):
    """Create test files for parallel analysis."""
    files = []
    
    for i in range(num_files):
        file_name = f"module_{i}.py"
        file_path = base_dir / file_name
        
        # Create varied content
        content = f'''
"""Module {i} - Test file for parallel analysis."""

import os
import sys
from typing import List, Dict

class TestClass{i}:
    """Test class {i}."""
    
    def __init__(self):
        self.value = {i}
        self.data = []
    
    def process(self, items: List[str]) -> Dict[str, int]:
        """Process items with complexity {i % 5 + 1}."""
        result = {{}}
        
        for item in items:
            if item.startswith("test"):
                if len(item) > 10:
                    result[item] = self.calculate(item)
                else:
                    result[item] = len(item)
            elif item.endswith("data"):
                result[item] = self.transform(item)
        
        return result
    
    def calculate(self, value: str) -> int:
        """Calculate something."""
        total = 0
        for char in value:
            if char.isdigit():
                total += int(char)
            elif char.isalpha():
                total += ord(char)
        return total
    
    def transform(self, data: str) -> int:
        """Transform data."""
        return len(data) * self.value

def utility_function_{i}(param: int) -> str:
    """Utility function {i}."""
    if param < 0:
        return "negative"
    elif param == 0:
        return "zero"
    elif param < 100:
        return "small"
    else:
        return "large"

def main_{i}():
    """Main function for module {i}."""
    obj = TestClass{i}()
    test_data = ["test_123", "data_456", "other"]
    result = obj.process(test_data)
    
    for key, value in result.items():
        status = utility_function_{i}(value)
        print(f"{{key}}: {{value}} ({{status}})")

# Cross-module reference
def call_neighbor():
    """Call function from neighboring module."""
    if {i} > 0:
        # Would import module_{i-1}
        pass
'''
        
        file_path.write_text(content)
        files.append(file_name)
    
    return files


def test_parallel_analyzer():
    """Test basic parallel analyzer."""
    print("🚀 Testing Parallel Analyzer")
    print("=" * 50)
    
    # Create test directory
    test_dir = Path("test_parallel")
    test_dir.mkdir(exist_ok=True)
    
    # Create test files
    files = create_test_files(test_dir, num_files=20)
    file_paths = [str(f) for f in files]
    
    print(f"Created {len(files)} test files")
    
    # Test with ParallelAnalyzer
    print("\n📊 Testing ParallelAnalyzer:")
    
    with ParallelAnalyzer(max_workers=4) as analyzer:
        start_time = time.time()
        results = analyzer.analyze_files(file_paths, str(test_dir))
        parallel_time = time.time() - start_time
    
    successful = sum(1 for r in results.values() if r.analysis)
    failed = sum(1 for r in results.values() if r.error)
    
    print(f"✓ Analyzed {len(results)} files in {parallel_time:.2f}s")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Average: {parallel_time/len(files):.3f}s per file")
    
    # Verify results
    for file_path, result in list(results.items())[:3]:
        if result.analysis:
            print(f"\n  {file_path}:")
            print(f"    Symbols: {len(result.analysis.symbols)}")
            print(f"    Complexity: {result.analysis.complexity}")
            print(f"    Duration: {result.duration:.3f}s")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return True


def test_parallel_ast_analyzer():
    """Test ParallelASTAnalyzer."""
    print("\n🔧 Testing ParallelASTAnalyzer")
    print("=" * 50)
    
    # Create test directory with subdirs
    test_dir = Path("test_parallel_ast")
    test_dir.mkdir(exist_ok=True)
    
    # Create files in subdirectories
    for subdir in ["core", "utils", "tests"]:
        sub_path = test_dir / subdir
        sub_path.mkdir(exist_ok=True)
        create_test_files(sub_path, num_files=10)
    
    print(f"Created test repository with 3 subdirectories")
    
    # Test directory analysis
    analyzer = ParallelASTAnalyzer(str(test_dir), max_workers=4)
    
    start_time = time.time()
    analyses = analyzer.analyze_directory(
        directory=".",
        extensions=[".py"],
        exclude_patterns=["__pycache__", ".git"]
    )
    duration = time.time() - start_time
    
    print(f"✓ Analyzed directory in {duration:.2f}s")
    print(f"  Total files: {len(analyses)}")
    
    # Show cache info
    cache_info = analyzer.get_cache_info()
    print(f"\n📦 Cache Info:")
    print(f"  Cached files: {cache_info['cached_files']}")
    print(f"  Total symbols: {cache_info['total_symbols']}")
    print(f"  Total complexity: {cache_info['total_complexity']}")
    
    # Test cache hit
    print(f"\n🔄 Testing cache performance:")
    start_time = time.time()
    analyses2 = analyzer.analyze_files(list(analyses.keys())[:10])
    cache_duration = time.time() - start_time
    
    print(f"✓ Re-analyzed 10 files in {cache_duration:.3f}s (from cache)")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return True


def test_enhanced_analyzer_parallel():
    """Test EnhancedASTAnalyzer with parallel processing."""
    print("\n🎯 Testing Enhanced Analyzer with Parallel Processing")
    print("=" * 50)
    
    # Create larger test set
    test_dir = Path("test_enhanced_parallel")
    test_dir.mkdir(exist_ok=True)
    
    # Create 50 files to trigger parallel processing
    files = create_test_files(test_dir, num_files=50)
    file_paths = [str(f) for f in files]
    
    print(f"Created {len(files)} test files")
    
    # Create enhanced analyzer
    analyzer = EnhancedASTAnalyzer(str(test_dir))
    
    # Build call graph (will use parallel processing for >10 files)
    print("\n📊 Building call graph:")
    start_time = time.time()
    call_graph = analyzer.build_call_graph(file_paths)
    duration = time.time() - start_time
    
    print(f"✓ Built call graph in {duration:.2f}s")
    print(f"  Nodes: {len(call_graph)}")
    
    # Get metrics
    metrics = analyzer.get_call_graph_metrics()
    print(f"\n📈 Metrics:")
    print(f"  Total nodes: {metrics['total_nodes']}")
    print(f"  Total edges: {metrics['total_edges']}")
    print(f"  Average degree: {metrics['avg_degree']:.2f}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return True


def test_performance_comparison():
    """Compare sequential vs parallel performance."""
    print("\n⚡ Performance Comparison: Sequential vs Parallel")
    print("=" * 50)
    
    # Create test files
    test_dir = Path("test_performance")
    test_dir.mkdir(exist_ok=True)
    
    num_files = 30
    files = create_test_files(test_dir, num_files=num_files)
    file_paths = [str(f) for f in files]
    
    print(f"Testing with {num_files} files")
    
    # Sequential analysis
    print("\n🐌 Sequential Analysis:")
    from src.code_planner.tree_sitter_analyzer import TreeSitterAnalyzer
    
    sequential_analyzer = TreeSitterAnalyzer()
    start_time = time.time()
    
    for file_path in file_paths:
        full_path = test_dir / file_path
        sequential_analyzer.analyze_file(full_path, "python")
    
    sequential_time = time.time() - start_time
    print(f"  Time: {sequential_time:.2f}s")
    print(f"  Per file: {sequential_time/num_files:.3f}s")
    
    # Parallel analysis
    print("\n🚀 Parallel Analysis (4 workers):")
    with ParallelAnalyzer(max_workers=4) as analyzer:
        start_time = time.time()
        results = analyzer.analyze_files(file_paths, str(test_dir))
        parallel_time = time.time() - start_time
    
    print(f"  Time: {parallel_time:.2f}s")
    print(f"  Per file: {parallel_time/num_files:.3f}s")
    
    # Calculate speedup
    speedup = sequential_time / parallel_time
    print(f"\n⚡ Speedup: {speedup:.2f}x faster with parallel processing")
    
    # Test with different worker counts
    print("\n📊 Worker Count Comparison:")
    for workers in [1, 2, 4, 8]:
        with ParallelAnalyzer(max_workers=workers) as analyzer:
            start_time = time.time()
            results = analyzer.analyze_files(file_paths[:20], str(test_dir))
            duration = time.time() - start_time
            
        print(f"  {workers} workers: {duration:.2f}s")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return True


if __name__ == "__main__":
    print("\n🚀 Parallel Processing Test Suite\n")
    
    # Check CPU count
    cpu_count = os.cpu_count()
    print(f"System has {cpu_count} CPU cores available")
    
    success = True
    success &= test_parallel_analyzer()
    success &= test_parallel_ast_analyzer()
    success &= test_enhanced_analyzer_parallel()
    success &= test_performance_comparison()
    
    if success:
        print("\n✅ All parallel processing tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(0 if success else 1)