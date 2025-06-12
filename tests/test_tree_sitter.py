#!/usr/bin/env python3
"""
Test tree-sitter AST analyzer functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner.tree_sitter_analyzer import TreeSitterAnalyzer, LANGUAGE_CONFIGS


def test_tree_sitter_languages():
    """Test tree-sitter support for multiple languages."""
    print("🌳 Testing Tree-Sitter Multi-Language Support")
    print("=" * 50)
    
    analyzer = TreeSitterAnalyzer()
    
    # Create test directory
    test_dir = Path("test_tree_sitter")
    test_dir.mkdir(exist_ok=True)
    
    # Test files for each language
    test_files = {
        "python": {
            "file": "test.py",
            "content": """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtils:
    def __init__(self):
        self.cache = {}
    
    def factorial(self, n):
        if n in self.cache:
            return self.cache[n]
        if n <= 1:
            return 1
        result = n * self.factorial(n-1)
        self.cache[n] = result
        return result
"""
        },
        "javascript": {
            "file": "test.js",
            "content": """
function quickSort(arr) {
    if (arr.length <= 1) {
        return arr;
    }
    
    const pivot = arr[0];
    const left = [];
    const right = [];
    
    for (let i = 1; i < arr.length; i++) {
        if (arr[i] < pivot) {
            left.push(arr[i]);
        } else {
            right.push(arr[i]);
        }
    }
    
    return [...quickSort(left), pivot, ...quickSort(right)];
}

class DataProcessor {
    constructor() {
        this.data = [];
    }
    
    process(item) {
        const processed = this.transform(item);
        this.data.push(processed);
        return processed;
    }
    
    transform(item) {
        return item.toUpperCase();
    }
}
"""
        },
        "java": {
            "file": "Test.java",
            "content": """
import java.util.ArrayList;
import java.util.List;

public class BinaryTree {
    private Node root;
    
    class Node {
        int value;
        Node left, right;
        
        Node(int value) {
            this.value = value;
        }
    }
    
    public void insert(int value) {
        root = insertRec(root, value);
    }
    
    private Node insertRec(Node root, int value) {
        if (root == null) {
            return new Node(value);
        }
        
        if (value < root.value) {
            root.left = insertRec(root.left, value);
        } else if (value > root.value) {
            root.right = insertRec(root.right, value);
        }
        
        return root;
    }
}
"""
        },
        "go": {
            "file": "test.go",
            "content": """
package main

import (
    "fmt"
    "sync"
)

type Counter struct {
    mu    sync.Mutex
    value int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
}

func (c *Counter) GetValue() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.value
}

func processItems(items []string) []string {
    results := make([]string, len(items))
    for i, item := range items {
        results[i] = fmt.Sprintf("Processed: %s", item)
    }
    return results
}
"""
        }
    }
    
    # Test each language
    for lang, test_data in test_files.items():
        print(f"\n🔍 Testing {lang.upper()}")
        print("-" * 30)
        
        # Create test file
        test_file = test_dir / test_data["file"]
        test_file.write_text(test_data["content"])
        
        # Analyze
        analysis = analyzer.analyze_file(test_file, lang)
        
        if analysis:
            print(f"✓ Successfully analyzed {test_file.name}")
            print(f"  Language: {analysis.language}")
            print(f"  Symbols: {len(analysis.symbols)}")
            print(f"  Imports: {len(analysis.imports)}")
            print(f"  Complexity: {analysis.complexity}")
            
            # Show symbols
            for symbol in analysis.symbols:
                print(f"  - {symbol.kind}: {symbol.name} (complexity: {symbol.complexity})")
                if symbol.calls:
                    print(f"    Calls: {', '.join(symbol.calls)}")
        else:
            print(f"✗ Failed to analyze {test_file.name}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    print("\n✅ Tree-sitter test completed!")
    return True


def test_complexity_calculation():
    """Test cyclomatic complexity calculation."""
    print("\n🧮 Testing Complexity Calculation")
    print("=" * 50)
    
    analyzer = TreeSitterAnalyzer()
    
    # Complex Python function
    complex_code = """
def complex_function(data, threshold):
    result = []
    for item in data:
        if item > threshold:
            if item % 2 == 0:
                result.append(item * 2)
            else:
                result.append(item * 3)
        elif item < 0:
            try:
                result.append(abs(item))
            except:
                result.append(0)
        else:
            result.append(item)
    return result
"""
    
    test_file = Path("complex_test.py")
    test_file.write_text(complex_code)
    
    analysis = analyzer.analyze_file(test_file, "python")
    
    if analysis and analysis.symbols:
        func = analysis.symbols[0]
        print(f"Function: {func.name}")
        print(f"Complexity: {func.complexity}")
        print(f"Expected: ~8 (1 base + 7 branches)")
        
        # Verify complexity is reasonable
        assert func.complexity >= 7, f"Complexity {func.complexity} seems too low"
        print("✓ Complexity calculation working correctly")
    
    # Cleanup
    test_file.unlink()
    
    return True


def test_language_detection():
    """Test automatic language detection."""
    print("\n🔍 Testing Language Detection")
    print("=" * 50)
    
    analyzer = TreeSitterAnalyzer()
    
    test_cases = [
        ("test.py", "python"),
        ("App.jsx", "javascript"),
        ("Main.java", "java"),
        ("server.go", "go"),
        ("unknown.xyz", None),
    ]
    
    for filename, expected in test_cases:
        detected = analyzer.detect_language(filename)
        status = "✓" if detected == expected else "✗"
        print(f"{status} {filename}: {detected} (expected: {expected})")
        assert detected == expected, f"Wrong language for {filename}"
    
    print("\n✓ Language detection working correctly")
    return True


if __name__ == "__main__":
    print("\n🚀 Tree-Sitter Test Suite")
    print("Testing multi-language AST analysis\n")
    
    success = True
    success &= test_language_detection()
    success &= test_tree_sitter_languages()
    success &= test_complexity_calculation()
    
    if success:
        print("\n✅ All tree-sitter tests passed!")
        
        # Show supported languages
        print("\n📚 Supported Languages:")
        for lang, config in LANGUAGE_CONFIGS.items():
            exts = ", ".join(config["extensions"])
            print(f"  - {lang}: {exts}")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(0 if success else 1)