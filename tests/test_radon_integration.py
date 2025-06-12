#!/usr/bin/env python3
"""
Test Radon integration for advanced Python complexity metrics.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner.radon_analyzer import RadonComplexityAnalyzer, RadonIntegration, RADON_AVAILABLE
from src.code_planner.ast_analyzer_v2 import EnhancedASTAnalyzer


def test_radon_analyzer():
    """Test basic Radon analyzer functionality."""
    if not RADON_AVAILABLE:
        print("⚠️  Radon not available - skipping tests")
        return True
    
    print("🎯 Testing Radon Analyzer")
    print("=" * 50)
    
    # Create test file
    test_dir = Path("test_radon")
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "complex_code.py"
    test_file.write_text("""
def simple_function():
    '''Simple function with complexity 1'''
    return 42

def moderate_function(x, y):
    '''Function with moderate complexity'''
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    else:
        if y > 0:
            return y - x
        else:
            return -x - y

def complex_function(data, mode='auto'):
    '''Function with high complexity'''
    result = []
    
    for item in data:
        if mode == 'auto':
            if isinstance(item, int):
                if item > 100:
                    result.append(item * 2)
                elif item > 50:
                    result.append(item + 10)
                elif item > 0:
                    result.append(item)
                else:
                    result.append(0)
            elif isinstance(item, str):
                if item.startswith('test'):
                    result.append(item.upper())
                elif item.endswith('data'):
                    result.append(item.lower())
                else:
                    result.append(item)
            else:
                result.append(str(item))
        elif mode == 'strict':
            if isinstance(item, int) and item > 0:
                result.append(item)
        else:
            result.append(item)
    
    return result

class Calculator:
    '''Class with various complexity methods'''
    
    def __init__(self):
        self.memory = 0
    
    def calculate(self, op, x, y=None):
        '''Method with cyclomatic complexity'''
        if op == 'add':
            return x + (y or 0)
        elif op == 'sub':
            return x - (y or 0)
        elif op == 'mul':
            return x * (y or 1)
        elif op == 'div':
            if y and y != 0:
                return x / y
            else:
                raise ValueError("Division by zero")
        elif op == 'pow':
            return x ** (y or 2)
        elif op == 'store':
            self.memory = x
            return x
        elif op == 'recall':
            return self.memory
        else:
            raise ValueError(f"Unknown operation: {op}")
    
    def fibonacci(self, n):
        '''Recursive method'''
        if n <= 1:
            return n
        return self.fibonacci(n-1) + self.fibonacci(n-2)
""")
    
    # Test analyzer
    analyzer = RadonComplexityAnalyzer()
    metrics = analyzer.analyze_file(test_file)
    
    assert metrics is not None, "Analysis failed"
    print("✓ Radon analysis completed")
    
    # Check cyclomatic complexity
    cc = metrics['cyclomatic_complexity']
    print(f"\n📊 Cyclomatic Complexity:")
    print(f"  Total: {cc['total']}")
    print(f"  Average: {cc['average']}")
    print(f"  Max: {cc['max']}")
    print(f"  Distribution: {cc['distribution']}")
    
    assert cc['total'] > 20, "Expected high total complexity"
    assert cc['max'] >= 10, "Expected at least one highly complex function"
    
    # Check Halstead metrics
    h = metrics['halstead_metrics']
    print(f"\n📏 Halstead Metrics:")
    print(f"  Volume: {h['volume']}")
    print(f"  Difficulty: {h['difficulty']}")
    print(f"  Effort: {h['effort']}")
    print(f"  Estimated bugs: {h['bugs']}")
    
    # Note: Halstead metrics might be 0 for some code
    if h['volume'] == 0:
        print("  (Note: Halstead metrics not available for this code)")
    
    # Check maintainability
    mi = metrics['maintainability_index']
    print(f"\n🏗️  Maintainability Index:")
    print(f"  Score: {mi['score']} ({mi['rank']})")
    print(f"  Description: {mi['description']}")
    
    # Check raw metrics
    raw = metrics['raw_metrics']
    print(f"\n📄 Raw Metrics:")
    print(f"  Lines of code: {raw['sloc']}")
    print(f"  Logical lines: {raw['lloc']}")
    print(f"  Comments: {raw['comments']} ({raw['comment_ratio']*100:.1f}%)")
    
    # Check function complexities
    print(f"\n🔍 Function Complexities:")
    for func in metrics['functions'][:5]:
        print(f"  {func['name']}: {func['complexity']} ({func['rank']})")
    
    assert len(metrics['functions']) >= 5, "Expected at least 5 functions"
    
    # Find complex_function
    complex_func = next((f for f in metrics['functions'] if f['name'] == 'complex_function'), None)
    assert complex_func is not None, "complex_function not found"
    assert complex_func['complexity'] >= 10, "complex_function should have high complexity"
    print(f"\n✓ complex_function has complexity {complex_func['complexity']}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return True


def test_radon_integration():
    """Test Radon integration with AST analyzer."""
    if not RADON_AVAILABLE:
        print("\n⚠️  Radon not available - skipping integration test")
        return True
    
    print("\n🔧 Testing Radon Integration")
    print("=" * 50)
    
    # Create test repository
    test_repo = Path("test_radon_integration")
    test_repo.mkdir(exist_ok=True)
    
    # Create Python file
    py_file = test_repo / "python_code.py"
    py_file.write_text("""
import os
import sys
from typing import List, Dict

def process_data(items: List[str]) -> Dict[str, int]:
    '''Process items with medium complexity'''
    result = {}
    
    for item in items:
        if item.startswith('test'):
            if len(item) > 10:
                result[item] = len(item) * 2
            else:
                result[item] = len(item)
        elif item.endswith('data'):
            result[item] = hash(item) % 100
        else:
            result[item] = 0
    
    return result

class DataProcessor:
    def __init__(self):
        self.cache = {}
    
    def analyze(self, data: str) -> int:
        '''Analyze data with caching'''
        if data in self.cache:
            return self.cache[data]
        
        score = 0
        for char in data:
            if char.isdigit():
                score += int(char)
            elif char.isalpha():
                if char.isupper():
                    score += ord(char) - ord('A') + 10
                else:
                    score += ord(char) - ord('a')
        
        self.cache[data] = score
        return score

# High complexity function
def validate_complex(value, rules):
    '''Highly complex validation function'''
    if not rules:
        return True
    
    for rule in rules:
        if rule['type'] == 'range':
            if 'min' in rule and value < rule['min']:
                return False
            if 'max' in rule and value > rule['max']:
                return False
        elif rule['type'] == 'list':
            if value not in rule['values']:
                return False
        elif rule['type'] == 'pattern':
            if not rule['pattern'].match(str(value)):
                return False
        elif rule['type'] == 'custom':
            if not rule['func'](value):
                return False
    
    return True
""")
    
    # Create JavaScript file for comparison
    js_file = test_repo / "javascript_code.js"
    js_file.write_text("""
function processArray(arr) {
    const result = [];
    
    for (let i = 0; i < arr.length; i++) {
        if (arr[i] > 0) {
            if (arr[i] % 2 === 0) {
                result.push(arr[i] * 2);
            } else {
                result.push(arr[i] + 1);
            }
        }
    }
    
    return result;
}

class DataHandler {
    constructor() {
        this.data = [];
    }
    
    addData(item) {
        if (typeof item === 'string') {
            this.data.push(item.toUpperCase());
        } else if (typeof item === 'number') {
            this.data.push(item * 2);
        } else {
            this.data.push(String(item));
        }
    }
}
""")
    
    # Create analyzer
    analyzer = EnhancedASTAnalyzer(str(test_repo))
    
    # Analyze Python file (should use Radon)
    print("\n📐 Analyzing Python file with Radon enhancement...")
    py_analysis = analyzer.analyze_file("python_code.py")
    
    assert py_analysis is not None, "Python analysis failed"
    print(f"✓ Analyzed {len(py_analysis.symbols)} symbols")
    
    # Check that complexities were enhanced by Radon
    process_data_symbol = next((s for s in py_analysis.symbols if s.name == "process_data"), None)
    assert process_data_symbol is not None, "process_data not found"
    print(f"✓ process_data complexity: {process_data_symbol.complexity}")
    
    validate_complex_symbol = next((s for s in py_analysis.symbols if s.name == "validate_complex"), None)
    assert validate_complex_symbol is not None, "validate_complex not found"
    assert validate_complex_symbol.complexity >= 5, "validate_complex should have high complexity"
    print(f"✓ validate_complex complexity: {validate_complex_symbol.complexity}")
    
    # Get Python complexity report
    report = analyzer.get_python_complexity_report("python_code.py")
    assert report is not None, "Failed to get complexity report"
    print(f"\n📋 Complexity Report:\n{report}")
    
    # Analyze JavaScript file (no Radon enhancement)
    print("\n📐 Analyzing JavaScript file (no Radon)...")
    js_analysis = analyzer.analyze_file("javascript_code.js")
    
    assert js_analysis is not None, "JavaScript analysis failed"
    print(f"✓ Analyzed {len(js_analysis.symbols)} symbols")
    
    # Get analyzer info
    info = analyzer.get_analyzer_info()
    print(f"\n📊 Analyzer Info:")
    print(f"  Tree-sitter: {info['tree_sitter_available']}")
    print(f"  Radon: {info['radon_available']}")
    print(f"  Enhanced Python: {info['enhanced_python_metrics']}")
    
    # Test repository summary
    print("\n📈 Getting repository complexity summary...")
    
    # Build call graph to populate cache
    analyzer.build_call_graph(["python_code.py", "javascript_code.js"])
    
    summary = analyzer.get_repository_complexity_summary()
    if 'error' not in summary:
        print(f"✓ Repository Summary:")
        print(f"  Total files: {summary.get('total_files', 0)}")
        print(f"  Total complexity: {summary.get('total_complexity', 0)}")
        print(f"  Average maintainability: {summary.get('average_maintainability', 0)}")
        
        if summary.get('most_complex_functions'):
            print(f"  Most complex function: {summary['most_complex_functions'][0]}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_repo, ignore_errors=True)
    
    return True


def test_complexity_comparison():
    """Compare complexity metrics with and without Radon."""
    if not RADON_AVAILABLE:
        print("\n⚠️  Radon not available - skipping comparison test")
        return True
    
    print("\n📊 Testing Complexity Comparison")
    print("=" * 50)
    
    # Create test file with known complexity
    test_dir = Path("test_complexity_comparison")
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "comparison.py"
    test_file.write_text("""
def nested_conditions(a, b, c, d):
    '''Function with many nested conditions'''
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    return "all positive"
                else:
                    return "d negative"
            else:
                if d > 0:
                    return "c negative, d positive"
                else:
                    return "c and d negative"
        else:
            if c > 0:
                if d > 0:
                    return "b negative, c and d positive"
                else:
                    return "b negative, c positive, d negative"
            else:
                return "b and c negative"
    else:
        if b > 0:
            return "a negative, b positive"
        else:
            return "a and b negative"

def switch_like(option):
    '''Function with many branches'''
    if option == 1:
        return "one"
    elif option == 2:
        return "two"
    elif option == 3:
        return "three"
    elif option == 4:
        return "four"
    elif option == 5:
        return "five"
    elif option == 6:
        return "six"
    elif option == 7:
        return "seven"
    elif option == 8:
        return "eight"
    elif option == 9:
        return "nine"
    elif option == 10:
        return "ten"
    else:
        return "other"
""")
    
    # Get Radon metrics directly
    radon_analyzer = RadonComplexityAnalyzer()
    radon_metrics = radon_analyzer.analyze_file(test_file)
    
    print("📏 Radon Metrics:")
    for func in radon_metrics['functions']:
        print(f"  {func['name']}: complexity {func['complexity']} ({func['rank']})")
    
    # Get tree-sitter metrics (without Radon)
    from src.code_planner.tree_sitter_analyzer import TreeSitterAnalyzer
    ts_analyzer = TreeSitterAnalyzer()
    ts_analysis = ts_analyzer.analyze_file(test_file, "python")
    
    print("\n🌳 Tree-sitter Metrics:")
    for symbol in ts_analysis.symbols:
        if symbol.kind == "function":
            print(f"  {symbol.name}: complexity {symbol.complexity}")
    
    # Create enhanced analyzer
    enhanced_analyzer = EnhancedASTAnalyzer(str(test_dir))
    enhanced_analysis = enhanced_analyzer.analyze_file("comparison.py")
    
    print("\n🚀 Enhanced Metrics (with Radon):")
    for symbol in enhanced_analysis.symbols:
        if symbol.kind == "function":
            print(f"  {symbol.name}: complexity {symbol.complexity}")
    
    # Verify Radon enhanced the metrics
    nested_symbol = next(s for s in enhanced_analysis.symbols if s.name == "nested_conditions")
    assert nested_symbol.complexity >= 9, "nested_conditions should have high Radon complexity"
    
    print(f"\n✓ Radon correctly identified high complexity in nested_conditions")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return True


if __name__ == "__main__":
    print("\n🚀 Radon Integration Test Suite\n")
    
    success = True
    success &= test_radon_analyzer()
    success &= test_radon_integration()
    success &= test_complexity_comparison()
    
    if success:
        print("\n✅ All Radon tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(0 if success else 1)