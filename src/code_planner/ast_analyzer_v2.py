"""
Enhanced AST analyzer that combines tree-sitter with fallback options.

This module provides the best available AST analysis for each language:
- Tree-sitter for supported languages (Python, JS, Java, Go)
- Python's built-in ast module as fallback for Python
- Basic analysis for unsupported languages
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from .ast_analyzer import Symbol, FileAnalysis, ASTAnalyzer as BaseASTAnalyzer
from .tree_sitter_analyzer import TreeSitterAnalyzer
from .call_graph_analyzer import CallGraphAnalyzer
from .cache_manager import create_cache_manager, CacheManager
from .parallel_analyzer import ParallelASTAnalyzer
from .radon_analyzer import RadonIntegration, RADON_AVAILABLE


class EnhancedASTAnalyzer(BaseASTAnalyzer):
    """Enhanced AST analyzer with tree-sitter support."""
    
    def __init__(self, repo_path: str, cache_manager: Optional[CacheManager] = None):
        super().__init__(repo_path)
        try:
            self.tree_sitter = TreeSitterAnalyzer()
            self.tree_sitter_available = True
        except Exception as e:
            print(f"Tree-sitter initialization failed: {e}")
            self.tree_sitter_available = False
        
        # Initialize NetworkX call graph
        self.call_graph = CallGraphAnalyzer()
        
        # Initialize cache manager
        self.cache = cache_manager or create_cache_manager()
        
        # Initialize Radon integration for Python files
        self.radon = RadonIntegration() if RADON_AVAILABLE else None
        if not RADON_AVAILABLE:
            print("Note: Radon not available. Python complexity metrics will be basic.")
    
    def analyze_file(self, file_path: str) -> Optional[FileAnalysis]:
        """Analyze a single file using the best available method."""
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return None
        
        # Check Redis cache first
        cached_analysis = self.cache.get_file_analysis(str(full_path))
        if cached_analysis:
            # Convert back to FileAnalysis object if needed
            if isinstance(cached_analysis, dict):
                # Reconstruct symbols
                symbols = []
                for s_dict in cached_analysis.get('symbols', []):
                    symbol = Symbol(
                        name=s_dict['name'],
                        kind=s_dict['kind'],
                        file_path=s_dict['file_path'],
                        line_start=s_dict['line_start'],
                        line_end=s_dict['line_end'],
                        calls=set(s_dict.get('calls', [])),
                        imports=set(s_dict.get('imports', [])),
                        complexity=s_dict.get('complexity', 1)
                    )
                    symbols.append(symbol)
                
                analysis = FileAnalysis(
                    path=cached_analysis['path'],
                    language=cached_analysis['language'],
                    symbols=symbols,
                    imports=cached_analysis['imports'],
                    exports=cached_analysis['exports'],
                    dependencies=set(cached_analysis['dependencies']),
                    complexity=cached_analysis['complexity']
                )
            else:
                analysis = cached_analysis
            
            # Update in-memory cache and call graph
            cache_key = str(full_path)
            self._symbol_cache[cache_key] = analysis
            self._update_call_graph(analysis)
            return analysis
        
        # Check in-memory cache
        cache_key = str(full_path)
        if cache_key in self._symbol_cache:
            return self._symbol_cache[cache_key]
        
        analysis = None
        
        # Try tree-sitter first if available
        if self.tree_sitter_available:
            language = self.tree_sitter.detect_language(file_path)
            if language:
                analysis = self.tree_sitter.analyze_file(full_path, language)
                if analysis:
                    # Update the path to be relative
                    analysis.path = file_path
        
        # Fallback to base analyzer if tree-sitter failed
        if not analysis:
            analysis = super().analyze_file(file_path)
        
        # Enhance Python files with Radon metrics
        if analysis and self.radon and file_path.endswith('.py'):
            # Convert analysis to dict for enhancement
            analysis_dict = self._analysis_to_dict(analysis)
            
            # Enhance with Radon
            enhanced_dict = self.radon.enhance_python_analysis(str(full_path), analysis_dict)
            
            # Update complexity in symbols
            if 'radon_metrics' in enhanced_dict:
                # Update symbol complexities
                for i, symbol in enumerate(analysis.symbols):
                    for func in enhanced_dict['radon_metrics']['functions']:
                        if symbol.name.endswith(func['name']) or symbol.name == func['name']:
                            analysis.symbols[i].complexity = func['complexity']
                
                # Update overall complexity
                analysis.complexity = enhanced_dict['complexity']
        
        # Cache result and update call graph
        if analysis:
            self._symbol_cache[cache_key] = analysis
            self._update_call_graph(analysis)
            
            # Store in Redis cache
            try:
                # Convert to dict for caching
                analysis_dict = {
                    'path': analysis.path,
                    'language': analysis.language,
                    'symbols': [
                        {
                            'name': s.name,
                            'kind': s.kind,
                            'file_path': s.file_path,
                            'line_start': s.line_start,
                            'line_end': s.line_end,
                            'calls': list(s.calls),
                            'imports': list(s.imports),
                            'complexity': s.complexity
                        } for s in analysis.symbols
                    ],
                    'imports': analysis.imports,
                    'exports': analysis.exports,
                    'dependencies': list(analysis.dependencies),
                    'complexity': analysis.complexity
                }
                self.cache.set_file_analysis(str(full_path), analysis_dict)
            except Exception as e:
                print(f"Failed to cache analysis: {e}")
        
        return analysis
    
    def get_analyzer_info(self) -> Dict[str, any]:
        """Get information about available analyzers."""
        info = {
            "tree_sitter_available": self.tree_sitter_available,
            "tree_sitter_languages": [],
            "fallback_languages": ["python", "javascript"],
            "cache_stats": self.cache.get_cache_stats(),
            "radon_available": RADON_AVAILABLE,
            "enhanced_python_metrics": RADON_AVAILABLE
        }
        
        if self.tree_sitter_available:
            from .tree_sitter_analyzer import LANGUAGE_CONFIGS
            info["tree_sitter_languages"] = list(LANGUAGE_CONFIGS.keys())
        
        return info
    
    def _update_call_graph(self, analysis: FileAnalysis):
        """Update the NetworkX call graph with analysis results."""
        # Add symbols to graph
        for symbol in analysis.symbols:
            node_id = self.call_graph.add_symbol(
                file=analysis.path,
                symbol=symbol.name,
                kind=symbol.kind,
                complexity=symbol.complexity,
                lines=(symbol.line_start, symbol.line_end)
            )
            
            # Add calls
            for called in symbol.calls:
                # Try to find the called symbol
                called_id = self._find_symbol_id(called, analysis.path)
                if called_id:
                    self.call_graph.add_call(node_id, called_id)
        
        # Add file dependencies
        for imp in analysis.imports:
            # Try to find the imported file
            import_file = self._resolve_import(imp, analysis.path)
            if import_file:
                self.call_graph.add_file_dependency(analysis.path, import_file, imp)
    
    def _find_symbol_id(self, symbol_name: str, current_file: str) -> Optional[str]:
        """Find the full ID of a symbol."""
        # First check in current file
        current_id = f"{current_file}:{symbol_name}"
        if current_id in self.call_graph.node_data:
            return current_id
        
        # Check all cached files for the symbol
        for file_path, analysis in self._symbol_cache.items():
            for symbol in analysis.symbols:
                if symbol.name == symbol_name or symbol.name.endswith(f".{symbol_name}"):
                    return f"{analysis.path}:{symbol.name}"
        
        return None
    
    def _resolve_import(self, import_name: str, current_file: str) -> Optional[str]:
        """Resolve an import to a file path."""
        # Simple heuristic - look for matching files in cache
        for file_path in self._symbol_cache:
            if import_name in file_path or file_path.endswith(f"{import_name}.py"):
                return self._symbol_cache[file_path].path
        return None
    
    def build_call_graph(self, files: List[str]) -> Dict[str, Set[str]]:
        """Build call graph using NetworkX (overrides base method)."""
        # Use parallel analysis for large file sets
        if len(files) > 10:
            self._analyze_files_parallel(files)
        else:
            # Analyze all files sequentially for small sets
            for file_path in files:
                self.analyze_file(file_path)
        
        # Return NetworkX-based call graph
        result = {}
        for node in self.call_graph.graph.nodes():
            callees = set(self.call_graph.get_callees(node))
            if callees:
                result[node] = callees
        
        # Also update the legacy _call_graph for compatibility
        self._call_graph = result
        
        return result
    
    def _analyze_files_parallel(self, files: List[str]):
        """Analyze multiple files in parallel."""
        print(f"Using parallel analysis for {len(files)} files...")
        
        # Create parallel analyzer
        parallel = ParallelASTAnalyzer(str(self.repo_path))
        
        # Analyze files
        analyses = parallel.analyze_files(files, show_progress=True)
        
        # Update caches and call graph
        for file_path, analysis in analyses.items():
            if analysis:
                # Update caches
                cache_key = str(self.repo_path / file_path)
                self._symbol_cache[cache_key] = analysis
                self._update_call_graph(analysis)
                
                # Store in Redis cache
                try:
                    self.cache.set_file_analysis(cache_key, self._analysis_to_dict(analysis))
                except Exception as e:
                    print(f"Failed to cache {file_path}: {e}")
    
    def _analysis_to_dict(self, analysis: FileAnalysis) -> dict:
        """Convert FileAnalysis to dict for caching."""
        return {
            'path': analysis.path,
            'language': analysis.language,
            'symbols': [
                {
                    'name': s.name,
                    'kind': s.kind,
                    'file_path': s.file_path,
                    'line_start': s.line_start,
                    'line_end': s.line_end,
                    'calls': list(s.calls),
                    'imports': list(s.imports),
                    'complexity': s.complexity
                } for s in analysis.symbols
            ],
            'imports': analysis.imports,
            'exports': analysis.exports,
            'dependencies': list(analysis.dependencies),
            'complexity': analysis.complexity
        }
    
    def calculate_impact(self, changed_files: List[str]) -> Set[str]:
        """Calculate impact using NetworkX graph analysis."""
        # Find all symbols in changed files
        changed_symbols = []
        for file_path in changed_files:
            for node_id, data in self.call_graph.graph.nodes(data=True):
                if data.get('file') == file_path:
                    changed_symbols.append(node_id)
        
        # Get impact set from call graph
        impact_symbols = self.call_graph.get_impact_set(changed_symbols)
        
        # Extract unique files
        impacted_files = set()
        for symbol_id in impact_symbols:
            if symbol_id in self.call_graph.node_data:
                impacted_files.add(self.call_graph.node_data[symbol_id].file)
        
        return impacted_files
    
    def get_call_graph_metrics(self) -> Dict[str, any]:
        """Get metrics from the NetworkX call graph."""
        return self.call_graph.get_complexity_metrics()
    
    def get_python_complexity_report(self, file_path: str) -> Optional[str]:
        """
        Get detailed Python complexity report using Radon.
        
        Args:
            file_path: Relative path to Python file
            
        Returns:
            Formatted complexity report or None
        """
        if not self.radon or not file_path.endswith('.py'):
            return None
        
        full_path = self.repo_path / file_path
        return self.radon.get_complexity_report(str(full_path))
    
    def get_repository_complexity_summary(self) -> Dict[str, any]:
        """
        Get complexity summary for all Python files in the repository.
        
        Returns:
            Summary statistics including most complex functions
        """
        if not self.radon:
            return {"error": "Radon not available"}
        
        # Analyze all Python files in cache
        python_files = {}
        for cache_key, analysis in self._symbol_cache.items():
            if analysis.path.endswith('.py'):
                full_path = Path(cache_key)
                if full_path.exists():
                    metrics = self.radon.analyzer.analyze_file(full_path)
                    if metrics:
                        python_files[analysis.path] = metrics
        
        if not python_files:
            return {"error": "No Python files analyzed"}
        
        return self.radon.analyzer.get_summary_stats(python_files)