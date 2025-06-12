"""
Tree-sitter based AST analyzer for multi-language support.

This module provides language-agnostic AST parsing using tree-sitter,
supporting multiple programming languages with unified interface.
"""

import tree_sitter
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_java
import tree_sitter_go
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from .ast_analyzer import Symbol, FileAnalysis


# Language configurations
LANGUAGE_CONFIGS = {
    "python": {
        "parser": tree_sitter_python,
        "extensions": [".py"],
        "function_types": ["function_definition"],
        "class_types": ["class_definition"],
        "method_types": ["function_definition"],  # Inside class
        "import_types": ["import_statement", "import_from_statement"],
        "call_types": ["call"],
    },
    "javascript": {
        "parser": tree_sitter_javascript,
        "extensions": [".js", ".jsx"],
        "function_types": ["function_declaration", "arrow_function", "function_expression"],
        "class_types": ["class_declaration"],
        "method_types": ["method_definition"],
        "import_types": ["import_statement"],
        "call_types": ["call_expression"],
    },
    "java": {
        "parser": tree_sitter_java,
        "extensions": [".java"],
        "function_types": ["method_declaration"],
        "class_types": ["class_declaration"],
        "method_types": ["method_declaration"],
        "import_types": ["import_declaration"],
        "call_types": ["method_invocation"],
    },
    "go": {
        "parser": tree_sitter_go,
        "extensions": [".go"],
        "function_types": ["function_declaration", "method_declaration"],
        "class_types": ["type_declaration"],  # Go doesn't have classes, but has types
        "method_types": ["method_declaration"],
        "import_types": ["import_declaration"],
        "call_types": ["call_expression"],
    },
}


class TreeSitterAnalyzer:
    """AST analyzer using tree-sitter for multi-language support."""
    
    def __init__(self):
        self.parsers = {}
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """Initialize tree-sitter parsers for each language."""
        for lang, config in LANGUAGE_CONFIGS.items():
            # New tree-sitter API
            language = tree_sitter.Language(config["parser"].language())
            parser = tree_sitter.Parser(language)
            self.parsers[lang] = parser
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        for lang, config in LANGUAGE_CONFIGS.items():
            if ext in config["extensions"]:
                return lang
        return None
    
    def analyze_file(self, file_path: Path, language: Optional[str] = None) -> Optional[FileAnalysis]:
        """Analyze a file using tree-sitter."""
        if not file_path.exists():
            return None
        
        # Detect language if not provided
        if not language:
            language = self.detect_language(str(file_path))
            if not language:
                return None
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Parse with tree-sitter
            parser = self.parsers.get(language)
            if not parser:
                return None
            
            tree = parser.parse(content)
            
            # Extract symbols
            symbols = self._extract_symbols(tree, content, str(file_path), language)
            imports = self._extract_imports(tree, content, language)
            
            # Calculate complexity
            total_complexity = sum(s.complexity for s in symbols)
            
            return FileAnalysis(
                path=str(file_path),
                language=language,
                symbols=symbols,
                imports=imports,
                exports=[s.name for s in symbols if s.kind in ('function', 'class')],
                dependencies=self._extract_dependencies(imports),
                complexity=total_complexity
            )
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _extract_symbols(self, tree, content: bytes, file_path: str, language: str) -> List[Symbol]:
        """Extract symbols from the AST."""
        symbols = []
        config = LANGUAGE_CONFIGS[language]
        
        def visit_node(node, parent_class=None):
            # Extract functions
            if node.type in config["function_types"]:
                symbol = self._extract_function(node, content, file_path, language, parent_class)
                if symbol:
                    symbols.append(symbol)
            
            # Extract classes
            elif node.type in config["class_types"]:
                symbol = self._extract_class(node, content, file_path, language)
                if symbol:
                    symbols.append(symbol)
                    # Visit children to find methods
                    for child in node.children:
                        visit_node(child, parent_class=symbol.name)
            
            # Recurse for all children
            else:
                for child in node.children:
                    visit_node(child, parent_class)
        
        visit_node(tree.root_node)
        return symbols
    
    def _extract_function(self, node, content: bytes, file_path: str, language: str, parent_class: Optional[str]) -> Optional[Symbol]:
        """Extract function information from node."""
        config = LANGUAGE_CONFIGS[language]
        
        # Get function name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
        
        # Determine if it's a method or function
        kind = "method" if parent_class else "function"
        if parent_class:
            name = f"{parent_class}.{name}"
        
        # Calculate complexity
        complexity = self._calculate_complexity(node)
        
        # Extract function calls
        calls = self._extract_calls(node, content, language)
        
        return Symbol(
            name=name,
            kind=kind,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            calls=calls,
            complexity=complexity
        )
    
    def _extract_class(self, node, content: bytes, file_path: str, language: str) -> Optional[Symbol]:
        """Extract class information from node."""
        # Get class name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
        
        # Count methods as complexity
        method_count = 0
        config = LANGUAGE_CONFIGS[language]
        for child in node.children:
            if child.type in config["method_types"]:
                method_count += 1
        
        return Symbol(
            name=name,
            kind="class",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            complexity=1 + method_count
        )
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a node."""
        complexity = 1
        
        # Control flow keywords that increase complexity
        complexity_types = {
            "if_statement", "elif_clause", "else_clause",
            "while_statement", "for_statement", "for_in_statement",
            "try_statement", "except_clause", "catch_clause",
            "case_statement", "switch_statement",
            "conditional_expression", "ternary_expression"
        }
        
        def count_complexity(n):
            nonlocal complexity
            if n.type in complexity_types:
                complexity += 1
            for child in n.children:
                count_complexity(child)
        
        count_complexity(node)
        return complexity
    
    def _extract_calls(self, node, content: bytes, language: str) -> Set[str]:
        """Extract function calls from a node."""
        calls = set()
        config = LANGUAGE_CONFIGS[language]
        
        def find_calls(n):
            if n.type in config["call_types"]:
                # Get the function being called
                if n.children:
                    func_node = n.children[0]
                    if func_node.type == "identifier":
                        func_name = content[func_node.start_byte:func_node.end_byte].decode('utf-8')
                        calls.add(func_name)
                    elif func_node.type == "attribute" and language == "python":
                        # Handle method calls like obj.method()
                        for child in func_node.children:
                            if child.type == "identifier":
                                method_name = content[child.start_byte:child.end_byte].decode('utf-8')
                                calls.add(method_name)
                                break
            
            for child in n.children:
                find_calls(child)
        
        find_calls(node)
        return calls
    
    def _extract_imports(self, tree, content: bytes, language: str) -> List[str]:
        """Extract import statements."""
        imports = []
        config = LANGUAGE_CONFIGS[language]
        
        def find_imports(node):
            if node.type in config["import_types"]:
                # Extract the module name
                import_text = content[node.start_byte:node.end_byte].decode('utf-8')
                
                if language == "python":
                    # Handle "import x" and "from x import y"
                    parts = import_text.split()
                    if parts[0] == "import":
                        imports.append(parts[1].split('.')[0])
                    elif parts[0] == "from" and len(parts) > 1:
                        imports.append(parts[1].split('.')[0])
                
                elif language == "javascript":
                    # Handle import x from 'module'
                    if "from" in import_text:
                        module = import_text.split("from")[-1].strip().strip("'\"`;")
                        imports.append(module)
                
                elif language == "java":
                    # Handle import com.example.Class;
                    if "import" in import_text:
                        module = import_text.replace("import", "").strip().rstrip(";")
                        imports.append(module.split('.')[0] if '.' in module else module)
                
                elif language == "go":
                    # Handle import "fmt" or import ( "fmt" "os" )
                    if '"' in import_text:
                        for part in import_text.split('"'):
                            if part and part not in ['import', '(', ')', ' ', '\n']:
                                imports.append(part.strip())
            
            for child in node.children:
                find_imports(child)
        
        find_imports(tree.root_node)
        return imports
    
    def _extract_dependencies(self, imports: List[str]) -> Set[str]:
        """Extract package dependencies from imports."""
        deps = set()
        for imp in imports:
            # Skip relative imports and standard library
            if not imp.startswith('.') and not imp.startswith('_'):
                # Get top-level package
                deps.add(imp.split('.')[0] if '.' in imp else imp)
        return deps