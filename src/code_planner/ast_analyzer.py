"""
AST Analysis for Code Understanding.

Provides language-agnostic AST parsing and analysis capabilities
to understand code structure, dependencies, and complexity.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Symbol:
    """Represents a code symbol (function, class, etc.)."""
    name: str
    kind: str  # function, class, method, variable
    file_path: str
    line_start: int
    line_end: int
    calls: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)
    complexity: int = 1


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    path: str
    language: str
    symbols: List[Symbol]
    imports: List[str]
    exports: List[str]
    dependencies: Set[str]
    complexity: int


class ASTAnalyzer:
    """Analyzes code structure using AST parsing."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self._symbol_cache: Dict[str, FileAnalysis] = {}
        self._call_graph: Dict[str, Set[str]] = defaultdict(set)
    
    def analyze_file(self, file_path: str) -> Optional[FileAnalysis]:
        """Analyze a single file and extract symbols, dependencies, etc."""
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return None
            
        # Check cache
        cache_key = str(full_path)
        if cache_key in self._symbol_cache:
            return self._symbol_cache[cache_key]
        
        language = self._detect_language(file_path)
        
        if language == "python":
            analysis = self._analyze_python(full_path, file_path)
        elif language == "javascript":
            analysis = self._analyze_javascript(full_path, file_path)
        else:
            # Basic analysis for unsupported languages
            analysis = self._analyze_generic(full_path, file_path, language)
        
        # Cache result
        self._symbol_cache[cache_key] = analysis
        return analysis
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
        }
        return language_map.get(ext, "unknown")
    
    def _analyze_python(self, full_path: Path, rel_path: str) -> FileAnalysis:
        """Analyze Python file using ast module."""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(full_path))
            
            symbols = []
            imports = []
            dependencies = set()
            
            # Extract symbols and analyze
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbol = self._extract_python_function(node, rel_path)
                    symbols.append(symbol)
                    
                elif isinstance(node, ast.ClassDef):
                    symbol = self._extract_python_class(node, rel_path)
                    symbols.append(symbol)
                    
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imp = self._extract_python_import(node)
                    imports.append(imp)
                    dependencies.add(imp.split('.')[0])
            
            # Calculate file complexity
            total_complexity = sum(s.complexity for s in symbols)
            
            # Exports (top-level symbols)
            exports = [s.name for s in symbols if s.kind in ('function', 'class')]
            
            return FileAnalysis(
                path=rel_path,
                language="python",
                symbols=symbols,
                imports=imports,
                exports=exports,
                dependencies=dependencies,
                complexity=total_complexity
            )
            
        except Exception as e:
            # Return basic analysis on parse error
            return FileAnalysis(
                path=rel_path,
                language="python",
                symbols=[],
                imports=[],
                exports=[],
                dependencies=set(),
                complexity=1
            )
    
    def _extract_python_function(self, node: ast.FunctionDef, file_path: str) -> Symbol:
        """Extract function information from AST node."""
        # Calculate cyclomatic complexity (simplified)
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        
        # Extract function calls
        calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                calls.add(child.func.id)
        
        return Symbol(
            name=node.name,
            kind="function",
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            calls=calls,
            complexity=complexity
        )
    
    def _extract_python_class(self, node: ast.ClassDef, file_path: str) -> Symbol:
        """Extract class information from AST node."""
        # Count methods as complexity
        complexity = 1 + sum(1 for n in node.body if isinstance(n, ast.FunctionDef))
        
        return Symbol(
            name=node.name,
            kind="class",
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            complexity=complexity
        )
    
    def _extract_python_import(self, node) -> str:
        """Extract import statement."""
        if isinstance(node, ast.Import):
            return node.names[0].name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            return module
        return ""
    
    def _analyze_javascript(self, full_path: Path, rel_path: str) -> FileAnalysis:
        """Basic JavaScript analysis using regex (simplified)."""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            symbols = []
            imports = []
            dependencies = set()
            
            # Extract functions (basic regex)
            func_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)'
            for match in re.finditer(func_pattern, content):
                name = match.group(1) or match.group(2)
                if name:
                    symbols.append(Symbol(
                        name=name,
                        kind="function",
                        file_path=rel_path,
                        line_start=content[:match.start()].count('\n') + 1,
                        line_end=content[:match.start()].count('\n') + 1,
                        complexity=1
                    ))
            
            # Extract imports
            import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
            for match in re.finditer(import_pattern, content):
                module = match.group(1)
                imports.append(module)
                if not module.startswith('.'):
                    dependencies.add(module.split('/')[0])
            
            return FileAnalysis(
                path=rel_path,
                language="javascript",
                symbols=symbols,
                imports=imports,
                exports=[s.name for s in symbols],
                dependencies=dependencies,
                complexity=len(symbols)
            )
            
        except Exception:
            return FileAnalysis(
                path=rel_path,
                language="javascript",
                symbols=[],
                imports=[],
                exports=[],
                dependencies=set(),
                complexity=1
            )
    
    def _analyze_generic(self, full_path: Path, rel_path: str, language: str) -> FileAnalysis:
        """Generic analysis for unsupported languages."""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Basic complexity: count control flow keywords
            complexity = 1
            for line in lines:
                if any(keyword in line for keyword in ['if', 'for', 'while', 'switch', 'case']):
                    complexity += 1
            
            return FileAnalysis(
                path=rel_path,
                language=language,
                symbols=[],
                imports=[],
                exports=[],
                dependencies=set(),
                complexity=complexity
            )
            
        except Exception:
            return FileAnalysis(
                path=rel_path,
                language=language,
                symbols=[],
                imports=[],
                exports=[],
                dependencies=set(),
                complexity=1
            )
    
    def build_call_graph(self, files: List[str]) -> Dict[str, Set[str]]:
        """Build a call graph for the given files."""
        # Analyze all files first
        for file_path in files:
            self.analyze_file(file_path)
        
        # Build symbol index
        symbol_to_file = {}
        for analysis in self._symbol_cache.values():
            for symbol in analysis.symbols:
                key = f"{symbol.file_path}:{symbol.name}"
                symbol_to_file[symbol.name] = key
        
        # Build call graph
        call_graph = defaultdict(set)
        for analysis in self._symbol_cache.values():
            for symbol in analysis.symbols:
                caller = f"{symbol.file_path}:{symbol.name}"
                for called in symbol.calls:
                    if called in symbol_to_file:
                        call_graph[caller].add(symbol_to_file[called])
        
        return dict(call_graph)
    
    def calculate_impact(self, changed_files: List[str]) -> Set[str]:
        """Calculate which files might be impacted by changes."""
        impacted = set(changed_files)
        
        # Add files that import changed files
        for file_path, analysis in self._symbol_cache.items():
            for dep in analysis.dependencies:
                for changed in changed_files:
                    if dep in changed or changed in dep:
                        impacted.add(analysis.path)
        
        return impacted