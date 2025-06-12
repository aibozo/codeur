#!/usr/bin/env python3
"""
Test NetworkX call graph functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner.ast_analyzer_v2 import EnhancedASTAnalyzer
from src.code_planner.call_graph_analyzer import CallGraphAnalyzer


def test_call_graph_creation():
    """Test creating and analyzing a call graph."""
    print("🔗 Testing NetworkX Call Graph")
    print("=" * 50)
    
    # Create test repository
    test_repo = Path("test_networkx_repo")
    test_repo.mkdir(exist_ok=True)
    
    # Create test files with dependencies
    src_dir = test_repo / "src"
    src_dir.mkdir(exist_ok=True)
    
    # main.py - entry point
    (src_dir / "main.py").write_text("""
from utils import process_data, validate_input
from calculator import Calculator

def main():
    data = get_user_input()
    if validate_input(data):
        calc = Calculator()
        result = calc.compute(data)
        processed = process_data(result)
        display_result(processed)

def get_user_input():
    return input("Enter data: ")

def display_result(result):
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""")
    
    # utils.py - utility functions
    (src_dir / "utils.py").write_text("""
def process_data(data):
    cleaned = clean_data(data)
    normalized = normalize_data(cleaned)
    return normalized

def clean_data(data):
    # Remove unwanted characters
    return str(data).strip()

def normalize_data(data):
    # Normalize the data
    return data.lower()

def validate_input(data):
    if not data:
        return False
    return is_valid_format(data)

def is_valid_format(data):
    # Check format
    return True
""")
    
    # calculator.py - main logic
    (src_dir / "calculator.py").write_text("""
from utils import validate_input

class Calculator:
    def __init__(self):
        self.history = []
    
    def compute(self, data):
        if not validate_input(data):
            raise ValueError("Invalid input")
        
        result = self._perform_calculation(data)
        self.history.append(result)
        return result
    
    def _perform_calculation(self, data):
        # Complex calculation
        return len(data) * 42
    
    def get_history(self):
        return self.history
""")
    
    # Create analyzer
    analyzer = EnhancedASTAnalyzer(str(test_repo))
    
    # Analyze files
    files = ["src/main.py", "src/utils.py", "src/calculator.py"]
    call_graph = analyzer.build_call_graph(files)
    
    print(f"✓ Built call graph with {len(call_graph)} nodes")
    
    # Get metrics
    metrics = analyzer.get_call_graph_metrics()
    print(f"\n📊 Call Graph Metrics:")
    print(f"  Total nodes: {metrics['total_nodes']}")
    print(f"  Total edges: {metrics['total_edges']}")
    print(f"  Average degree: {metrics['avg_degree']:.2f}")
    print(f"  Max in-degree: {metrics['max_in_degree']}")
    print(f"  Max out-degree: {metrics['max_out_degree']}")
    print(f"  Circular dependencies: {metrics['circular_dependencies']}")
    
    # Show most complex functions
    print(f"\n🔥 Most Complex Functions:")
    for func, complexity in metrics['most_complex_functions'][:5]:
        print(f"  {func}: complexity={complexity}")
    
    # Show most connected functions
    print(f"\n🕸️ Most Connected Functions:")
    for func, degree in metrics['most_connected_functions'][:5]:
        print(f"  {func}: connections={degree}")
    
    # Test impact analysis
    print(f"\n💥 Impact Analysis:")
    impact = analyzer.calculate_impact(["src/utils.py"])
    print(f"  Changing utils.py impacts: {impact}")
    
    # Find circular dependencies
    circles = analyzer.call_graph.find_circular_dependencies()
    if circles:
        print(f"\n🔄 Circular Dependencies Found:")
        for circle in circles:
            print(f"  {' -> '.join(circle)}")
    else:
        print(f"\n✓ No circular dependencies found")
    
    # Test path finding
    print(f"\n🛤️ Call Paths:")
    path = analyzer.call_graph.get_call_path(
        "src/main.py:main",
        "src/utils.py:is_valid_format"
    )
    if path:
        print(f"  Path from main to is_valid_format: {' -> '.join(path)}")
    
    # Export to DOT format
    dot_graph = analyzer.call_graph.export_to_dot()
    dot_file = test_repo / "call_graph.dot"
    dot_file.write_text(dot_graph)
    print(f"\n✓ Exported call graph to {dot_file}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_repo, ignore_errors=True)
    
    return True


def test_graph_analyzer_directly():
    """Test CallGraphAnalyzer directly."""
    print("\n🔬 Testing CallGraphAnalyzer Directly")
    print("=" * 50)
    
    graph = CallGraphAnalyzer()
    
    # Create a sample graph
    # Module A
    graph.add_symbol("moduleA.py", "funcA1", "function", complexity=3)
    graph.add_symbol("moduleA.py", "funcA2", "function", complexity=2)
    
    # Module B
    graph.add_symbol("moduleB.py", "ClassB", "class")
    graph.add_symbol("moduleB.py", "ClassB.method1", "method", complexity=4)
    graph.add_symbol("moduleB.py", "funcB1", "function", complexity=1)
    
    # Add dependencies
    graph.add_call("moduleA.py:funcA1", "moduleA.py:funcA2")
    graph.add_call("moduleA.py:funcA1", "moduleB.py:funcB1")
    graph.add_call("moduleB.py:ClassB.method1", "moduleA.py:funcA2")
    graph.add_call("moduleA.py:funcA2", "moduleB.py:ClassB.method1")  # Circular!
    
    # Test features
    print("📊 Graph Structure:")
    print(f"  Nodes: {graph.graph.number_of_nodes()}")
    print(f"  Edges: {graph.graph.number_of_edges()}")
    
    # Find circular dependencies
    circles = graph.find_circular_dependencies()
    print(f"\n🔄 Circular Dependencies: {len(circles)}")
    for circle in circles:
        print(f"  {' -> '.join(circle)}")
    
    # Test impact analysis
    impact = graph.get_impact_set(["moduleA.py:funcA2"])
    print(f"\n💥 Impact of changing funcA2: {impact}")
    
    # Test dependency analysis
    deps = graph.get_dependency_set(["moduleB.py:ClassB.method1"])
    print(f"\n📦 Dependencies of ClassB.method1: {deps}")
    
    return True


if __name__ == "__main__":
    print("\n🚀 NetworkX Call Graph Test Suite\n")
    
    success = True
    success &= test_graph_analyzer_directly()
    success &= test_call_graph_creation()
    
    if success:
        print("\n✅ All NetworkX tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(0 if success else 1)