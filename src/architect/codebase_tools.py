"""
Codebase understanding tools for the Architect agent.

This module provides tools that allow the Architect to explore and understand
the codebase at various levels of detail, from high-level architecture to
specific code implementations.
"""

import os
import re
import ast
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComponentInfo:
    """Information about a code component."""
    path: str
    type: str  # "module", "class", "function", "file"
    name: str
    description: str
    imports: List[str]
    exports: List[str]
    dependencies: List[str]
    complexity: int
    loc: int  # lines of code


class CodebaseTools:
    """
    Tools for understanding and navigating the codebase.
    
    These tools help the Architect answer both high-level architectural questions
    and detailed implementation questions about the codebase.
    """
    
    def __init__(self, project_path: str, rag_client = None):
        self.project_path = Path(project_path)
        self.rag_client = rag_client
        
        # Cache for expensive operations
        self._tech_stack_cache = None
        self._pattern_cache = {}
        
    async def search_codebase(self, 
                            query: str, 
                            file_pattern: Optional[str] = None,
                            limit: int = 10) -> Dict[str, Any]:
        """
        Search for code patterns, functions, classes, or concepts in the codebase.
        
        This tool is your primary way to find relevant code when you need to understand
        how something is implemented or where certain functionality exists.
        
        Args:
            query: Natural language search query or code pattern
            file_pattern: Optional file pattern to limit search (e.g., "*.py", "src/**/*.js")
            limit: Maximum number of results to return
            
        Returns:
            Search results with code snippets and file locations
            
        When to use:
        - Finding where a feature is implemented: "authentication logic"
        - Looking for specific patterns: "database connections"
        - Finding usage examples: "how is caching implemented"
        - Locating configuration: "where are API keys stored"
        
        Examples:
            search_codebase("user authentication")
            search_codebase("class.*Controller", file_pattern="**/controllers/*.py")
            search_codebase("database configuration", limit=5)
        """
        try:
            results = []
            
            # Use RAG search if available
            if self.rag_client:
                rag_results = self.rag_client.query(query, top_k=limit)
                for doc in rag_results.get("documents", []):
                    results.append({
                        "file": doc.get("metadata", {}).get("source", "unknown"),
                        "content": doc.get("content", ""),
                        "relevance": doc.get("score", 0.0),
                        "type": "semantic_match"
                    })
            
            # Also do pattern-based search
            pattern_results = self._search_by_pattern(query, file_pattern, limit)
            results.extend(pattern_results)
            
            # Remove duplicates and sort by relevance
            seen = set()
            unique_results = []
            for r in results:
                key = f"{r['file']}:{r.get('line', 0)}"
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)
            
            unique_results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            
            return {
                "status": "success",
                "query": query,
                "results": unique_results[:limit],
                "total_found": len(unique_results)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}"
            }
    
    async def explore_file(self, 
                         file_path: str, 
                         focus_area: Optional[str] = None) -> Dict[str, Any]:
        """
        Read and analyze a specific file with optional focus on certain sections.
        
        Use this when you need to understand a specific file's structure, purpose,
        or implementation details.
        
        Args:
            file_path: Path to the file relative to project root
            focus_area: Optional area to focus on (e.g., "class UserAuth", "function validate")
            
        Returns:
            File content with structure analysis
            
        When to use:
        - Understanding a specific module's structure
        - Analyzing implementation details
        - Finding specific functions or classes within a file
        - Understanding file dependencies
        
        Examples:
            explore_file("src/auth/login.py")
            explore_file("src/models/user.py", focus_area="class User")
            explore_file("config/settings.py", focus_area="DATABASE")
        """
        try:
            full_path = self.project_path / file_path
            
            if not full_path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            content = full_path.read_text()
            
            # Basic file info
            info = {
                "status": "success",
                "file": file_path,
                "size": len(content),
                "lines": len(content.splitlines()),
                "language": self._detect_language(file_path)
            }
            
            # If it's a Python file, do AST analysis
            if file_path.endswith('.py'):
                ast_info = self._analyze_python_file(full_path, content)
                info.update(ast_info)
            
            # Focus on specific area if requested
            if focus_area:
                focused_content = self._extract_focus_area(content, focus_area, info.get("language"))
                info["focused_content"] = focused_content
            else:
                # Return full content with truncation if too large
                if len(content) > 5000:
                    info["content"] = content[:5000] + "\n... (truncated)"
                    info["truncated"] = True
                else:
                    info["content"] = content
            
            return info
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to explore file: {str(e)}"
            }
    
    async def find_symbol(self, 
                        symbol_name: str, 
                        symbol_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Find where a class, function, or variable is defined and used.
        
        This helps you understand how a specific piece of code is used throughout
        the codebase.
        
        Args:
            symbol_name: Name of the symbol to find
            symbol_type: Optional type filter ("class", "function", "variable", "import")
            
        Returns:
            Definition location and usage locations
            
        When to use:
        - Finding where a class is defined: find_symbol("UserModel", "class")
        - Tracking function usage: find_symbol("authenticate", "function")  
        - Understanding variable scope: find_symbol("API_KEY", "variable")
        - Finding import statements: find_symbol("requests", "import")
        
        Examples:
            find_symbol("DatabaseConnection", "class")
            find_symbol("validate_email")
            find_symbol("MAX_RETRIES", "variable")
        """
        try:
            definitions = []
            usages = []
            
            # Search for symbol definitions and usages
            for py_file in self.project_path.rglob("*.py"):
                if any(part.startswith('.') for part in py_file.parts):
                    continue  # Skip hidden directories
                    
                try:
                    content = py_file.read_text()
                    relative_path = py_file.relative_to(self.project_path)
                    
                    # Find definitions
                    if symbol_type in [None, "class"]:
                        for match in re.finditer(rf'^class\s+{symbol_name}\s*[\(:]', content, re.MULTILINE):
                            line_num = content[:match.start()].count('\n') + 1
                            definitions.append({
                                "file": str(relative_path),
                                "line": line_num,
                                "type": "class",
                                "context": self._get_line_context(content, line_num)
                            })
                    
                    if symbol_type in [None, "function"]:
                        for match in re.finditer(rf'^def\s+{symbol_name}\s*\(', content, re.MULTILINE):
                            line_num = content[:match.start()].count('\n') + 1
                            definitions.append({
                                "file": str(relative_path),
                                "line": line_num,
                                "type": "function",
                                "context": self._get_line_context(content, line_num)
                            })
                    
                    # Find usages (any occurrence that's not a definition)
                    for match in re.finditer(rf'\b{symbol_name}\b', content):
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.splitlines()[line_num - 1].strip()
                        
                        # Skip if it's a definition line
                        if not (line_content.startswith('class ') or line_content.startswith('def ')):
                            usages.append({
                                "file": str(relative_path),
                                "line": line_num,
                                "context": line_content
                            })
                            
                except Exception:
                    continue  # Skip files that can't be read
            
            return {
                "status": "success",
                "symbol": symbol_name,
                "type": symbol_type or "any",
                "definitions": definitions,
                "usages": usages[:20],  # Limit usages to prevent overwhelming output
                "total_usages": len(usages)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Symbol search failed: {str(e)}"
            }
    
    async def trace_imports(self, file_path: str) -> Dict[str, Any]:
        """
        Trace import dependencies for a file or module.
        
        Helps you understand what a module depends on and what depends on it.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Import graph showing dependencies
            
        When to use:
        - Understanding module dependencies
        - Finding circular imports
        - Analyzing coupling between modules
        - Planning refactoring
        
        Examples:
            trace_imports("src/api/routes.py")
            trace_imports("src/models/__init__.py")
        """
        try:
            full_path = self.project_path / file_path
            
            if not full_path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            # Get direct imports from the file
            imports = self._extract_imports(full_path)
            
            # Find who imports this file
            importers = self._find_importers(file_path)
            
            # Build dependency tree (limited depth to avoid recursion)
            dependency_tree = self._build_dependency_tree(file_path, depth=2)
            
            return {
                "status": "success",
                "file": file_path,
                "imports": imports,
                "imported_by": importers,
                "dependency_tree": dependency_tree,
                "metrics": {
                    "direct_dependencies": len(imports),
                    "dependents": len(importers),
                    "coupling_score": len(imports) + len(importers)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Import tracing failed: {str(e)}"
            }
    
    async def analyze_component(self, component_path: str) -> Dict[str, Any]:
        """
        Deep dive into a specific component or module structure.
        
        Provides comprehensive analysis of a component including its structure,
        dependencies, complexity, and purpose.
        
        Args:
            component_path: Path to component directory or main file
            
        Returns:
            Detailed component analysis
            
        When to use:
        - Understanding a module's architecture
        - Analyzing component complexity
        - Planning modifications to a component
        - Documenting component structure
        
        Examples:
            analyze_component("src/auth")
            analyze_component("src/api/v1")
            analyze_component("src/models/user.py")
        """
        try:
            path = self.project_path / component_path
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"Component not found: {component_path}"
                }
            
            # Determine if it's a file or directory
            if path.is_file():
                components = [self._analyze_file_component(path)]
            else:
                components = self._analyze_directory_component(path)
            
            # Aggregate metrics
            total_loc = sum(c.loc for c in components)
            total_complexity = sum(c.complexity for c in components)
            all_imports = set()
            all_exports = set()
            
            for comp in components:
                all_imports.update(comp.imports)
                all_exports.update(comp.exports)
            
            return {
                "status": "success",
                "component": component_path,
                "type": "file" if path.is_file() else "module",
                "structure": {
                    "files": len(components),
                    "total_loc": total_loc,
                    "avg_complexity": total_complexity / len(components) if components else 0,
                    "imports": list(all_imports),
                    "exports": list(all_exports)
                },
                "components": [
                    {
                        "path": c.path,
                        "type": c.type,
                        "name": c.name,
                        "description": c.description,
                        "complexity": c.complexity,
                        "loc": c.loc
                    }
                    for c in components[:10]  # Limit to prevent overwhelming output
                ],
                "recommendations": self._get_component_recommendations(components)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Component analysis failed: {str(e)}"
            }
    
    async def map_relationships(self, 
                              entry_point: str, 
                              depth: int = 2) -> Dict[str, Any]:
        """
        Map relationships between components starting from an entry point.
        
        Helps visualize how components interact and depend on each other.
        
        Args:
            entry_point: Starting point for relationship mapping
            depth: How many levels deep to trace (default: 2)
            
        Returns:
            Component relationship map
            
        When to use:
        - Understanding component interactions
        - Identifying tightly coupled components
        - Planning system modifications
        - Analyzing impact of changes
        
        Examples:
            map_relationships("src/api/routes.py")
            map_relationships("src/models", depth=3)
            map_relationships("src/auth/manager.py", depth=1)
        """
        try:
            relationships = {
                "nodes": {},
                "edges": []
            }
            
            visited = set()
            queue = [(entry_point, 0)]
            
            while queue:
                current_path, current_depth = queue.pop(0)
                
                if current_path in visited or current_depth > depth:
                    continue
                    
                visited.add(current_path)
                
                # Analyze current component
                path = self.project_path / current_path
                if not path.exists():
                    continue
                
                # Add node
                relationships["nodes"][current_path] = {
                    "type": "file" if path.is_file() else "directory",
                    "depth": current_depth
                }
                
                # Find relationships
                if path.is_file() and path.suffix == '.py':
                    imports = self._extract_imports(path)
                    for imp in imports:
                        # Convert import to file path
                        import_path = self._import_to_path(imp)
                        if import_path:
                            relationships["edges"].append({
                                "from": current_path,
                                "to": import_path,
                                "type": "imports"
                            })
                            
                            if current_depth < depth:
                                queue.append((import_path, current_depth + 1))
                
                elif path.is_dir():
                    # For directories, analyze all Python files
                    for py_file in path.glob("*.py"):
                        rel_path = py_file.relative_to(self.project_path)
                        if current_depth < depth:
                            queue.append((str(rel_path), current_depth + 1))
            
            # Calculate metrics
            metrics = self._calculate_relationship_metrics(relationships)
            
            return {
                "status": "success",
                "entry_point": entry_point,
                "depth": depth,
                "relationships": relationships,
                "metrics": metrics,
                "visualization_hint": "Use edges to draw dependency graph"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Relationship mapping failed: {str(e)}"
            }
    
    async def find_patterns(self, pattern_type: str = "all") -> Dict[str, Any]:
        """
        Identify design patterns and architectural patterns in the codebase.
        
        Helps understand the architectural decisions and patterns used.
        
        Args:
            pattern_type: Type of pattern to find ("all", "creational", "structural", 
                         "behavioral", "architectural")
            
        Returns:
            Identified patterns with examples
            
        When to use:
        - Understanding codebase architecture
        - Learning project conventions
        - Identifying refactoring opportunities
        - Ensuring consistency
        
        Examples:
            find_patterns()  # Find all patterns
            find_patterns("architectural")  # Focus on high-level patterns
            find_patterns("creational")  # Find factory, singleton, etc.
        """
        try:
            # Check cache first
            if pattern_type in self._pattern_cache:
                return self._pattern_cache[pattern_type]
            
            patterns = {
                "architectural": [],
                "creational": [],
                "structural": [],
                "behavioral": []
            }
            
            # Detect MVC/MVP/MVVM patterns
            if pattern_type in ["all", "architectural"]:
                mvc_pattern = self._detect_mvc_pattern()
                if mvc_pattern:
                    patterns["architectural"].append(mvc_pattern)
                
                layered = self._detect_layered_architecture()
                if layered:
                    patterns["architectural"].append(layered)
            
            # Detect creational patterns
            if pattern_type in ["all", "creational"]:
                singleton = self._detect_singleton_pattern()
                patterns["creational"].extend(singleton)
                
                factory = self._detect_factory_pattern()
                patterns["creational"].extend(factory)
            
            # Detect structural patterns
            if pattern_type in ["all", "structural"]:
                decorator = self._detect_decorator_pattern()
                patterns["structural"].extend(decorator)
                
                adapter = self._detect_adapter_pattern()
                patterns["structural"].extend(adapter)
            
            # Detect behavioral patterns
            if pattern_type in ["all", "behavioral"]:
                observer = self._detect_observer_pattern()
                patterns["behavioral"].extend(observer)
                
                strategy = self._detect_strategy_pattern()
                patterns["behavioral"].extend(strategy)
            
            result = {
                "status": "success",
                "pattern_type": pattern_type,
                "patterns": patterns if pattern_type == "all" else patterns.get(pattern_type, []),
                "summary": {
                    "total_patterns": sum(len(p) for p in patterns.values()),
                    "architectural": len(patterns["architectural"]),
                    "design_patterns": sum(len(patterns[k]) for k in ["creational", "structural", "behavioral"])
                }
            }
            
            # Cache result
            self._pattern_cache[pattern_type] = result
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Pattern detection failed: {str(e)}"
            }
    
    async def assess_tech_stack(self) -> Dict[str, Any]:
        """
        Identify technologies, frameworks, and libraries used in the project.
        
        Provides a comprehensive overview of the technical stack.
        
        Returns:
            Technology stack analysis
            
        When to use:
        - Understanding project dependencies
        - Planning integrations
        - Assessing technical debt
        - Making architectural decisions
        
        Example:
            assess_tech_stack()
        """
        try:
            # Use cache if available
            if self._tech_stack_cache:
                return self._tech_stack_cache
            
            tech_stack = {
                "languages": {},
                "frameworks": [],
                "libraries": [],
                "tools": [],
                "databases": [],
                "testing": []
            }
            
            # Analyze programming languages
            language_stats = self._analyze_languages()
            tech_stack["languages"] = language_stats
            
            # Analyze package files
            if (self.project_path / "requirements.txt").exists():
                tech_stack["libraries"].extend(self._parse_requirements())
            
            if (self.project_path / "package.json").exists():
                npm_info = self._parse_package_json()
                tech_stack["libraries"].extend(npm_info["dependencies"])
                tech_stack["tools"].extend(npm_info["devDependencies"])
            
            if (self.project_path / "Pipfile").exists():
                tech_stack["libraries"].extend(self._parse_pipfile())
            
            # Detect frameworks
            tech_stack["frameworks"] = self._detect_frameworks()
            
            # Detect databases
            tech_stack["databases"] = self._detect_databases()
            
            # Detect testing frameworks
            tech_stack["testing"] = self._detect_testing_frameworks()
            
            # Build summary
            result = {
                "status": "success",
                "tech_stack": tech_stack,
                "summary": {
                    "primary_language": max(language_stats.items(), key=lambda x: x[1])[0] if language_stats else "unknown",
                    "framework_count": len(tech_stack["frameworks"]),
                    "dependency_count": len(tech_stack["libraries"]),
                    "has_testing": len(tech_stack["testing"]) > 0,
                    "has_database": len(tech_stack["databases"]) > 0
                },
                "recommendations": self._get_tech_stack_recommendations(tech_stack)
            }
            
            # Cache result
            self._tech_stack_cache = result
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Tech stack assessment failed: {str(e)}"
            }
    
    async def find_entry_points(self) -> Dict[str, Any]:
        """
        Locate application entry points and main execution paths.
        
        Helps understand how the application starts and its main flows.
        
        Returns:
            Entry points and execution paths
            
        When to use:
        - Understanding application startup
        - Tracing execution flow
        - Debugging initialization issues
        - Planning architectural changes
        
        Example:
            find_entry_points()
        """
        try:
            entry_points = []
            
            # Common entry point patterns
            entry_patterns = [
                ("main.py", "Python main script"),
                ("app.py", "Flask/FastAPI application"),
                ("manage.py", "Django management script"),
                ("server.py", "Server entry point"),
                ("index.js", "Node.js entry point"),
                ("index.ts", "TypeScript entry point"),
                ("src/index.*", "Source index file"),
                ("src/main.*", "Source main file"),
                ("bin/*", "Executable scripts"),
                ("scripts/*", "Script files")
            ]
            
            for pattern, description in entry_patterns:
                for match in self.project_path.glob(pattern):
                    if match.is_file():
                        entry_points.append({
                            "file": str(match.relative_to(self.project_path)),
                            "type": description,
                            "executable": os.access(match, os.X_OK)
                        })
            
            # Look for __main__ blocks in Python files
            for py_file in self.project_path.rglob("*.py"):
                try:
                    content = py_file.read_text()
                    if "if __name__ == '__main__':" in content or "if __name__ == \"__main__\":" in content:
                        entry_points.append({
                            "file": str(py_file.relative_to(self.project_path)),
                            "type": "Python script with main block",
                            "executable": os.access(py_file, os.X_OK)
                        })
                except Exception:
                    continue
            
            # Look for setup.py entry points
            setup_py = self.project_path / "setup.py"
            if setup_py.exists():
                setup_entries = self._parse_setup_py_entries(setup_py)
                entry_points.extend(setup_entries)
            
            # Remove duplicates
            seen = set()
            unique_entries = []
            for entry in entry_points:
                if entry["file"] not in seen:
                    seen.add(entry["file"])
                    unique_entries.append(entry)
            
            return {
                "status": "success",
                "entry_points": unique_entries,
                "count": len(unique_entries),
                "has_main": any(e["type"].startswith("Python main") for e in unique_entries),
                "has_server": any("server" in e["file"].lower() for e in unique_entries),
                "has_cli": any(e["executable"] for e in unique_entries)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Entry point detection failed: {str(e)}"
            }
    
    async def analyze_data_flow(self, entry_point: str) -> Dict[str, Any]:
        """
        Trace data flow through the application from an entry point.
        
        Helps understand how data moves through the system.
        
        Args:
            entry_point: Starting point for data flow analysis (file path or function name)
            
        Returns:
            Data flow analysis
            
        When to use:
        - Understanding request handling
        - Tracking data transformations
        - Identifying data dependencies
        - Debugging data issues
        
        Examples:
            analyze_data_flow("src/api/routes.py")
            analyze_data_flow("handle_user_request")
        """
        try:
            # This is a simplified version - full implementation would use AST
            flow_path = []
            data_transformations = []
            
            # Find the entry point
            entry_file = None
            if os.path.exists(self.project_path / entry_point):
                entry_file = self.project_path / entry_point
            else:
                # Search for function
                for py_file in self.project_path.rglob("*.py"):
                    try:
                        content = py_file.read_text()
                        if f"def {entry_point}" in content:
                            entry_file = py_file
                            break
                    except Exception:
                        continue
            
            if not entry_file:
                return {
                    "status": "error",
                    "message": f"Entry point not found: {entry_point}"
                }
            
            # Analyze data flow (simplified)
            content = entry_file.read_text()
            
            # Look for function calls and data operations
            function_calls = re.findall(r'(\w+)\s*\([^)]*\)', content)
            data_ops = re.findall(r'(\w+)\s*=\s*([^=\n]+)', content)
            
            # Build flow path
            for i, func in enumerate(function_calls[:10]):  # Limit to prevent overflow
                flow_path.append({
                    "step": i + 1,
                    "operation": func,
                    "type": "function_call"
                })
            
            # Identify transformations
            for var, value in data_ops[:10]:
                if any(op in value for op in ['map', 'filter', 'transform', 'process']):
                    data_transformations.append({
                        "variable": var,
                        "transformation": value.strip()
                    })
            
            return {
                "status": "success",
                "entry_point": entry_point,
                "flow_path": flow_path,
                "data_transformations": data_transformations,
                "summary": {
                    "total_steps": len(flow_path),
                    "transformations": len(data_transformations),
                    "complexity": "simple" if len(flow_path) < 5 else "moderate" if len(flow_path) < 10 else "complex"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Data flow analysis failed: {str(e)}"
            }
    
    # Helper methods
    
    def _search_by_pattern(self, pattern: str, file_pattern: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Search for pattern in files."""
        results = []
        
        # Determine if it's a regex pattern
        is_regex = any(c in pattern for c in ['.*', '.+', '[', ']', '^', '$', '\\'])
        
        if is_regex:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                return []
        else:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)
        
        # Search files
        search_pattern = file_pattern or "**/*.py"
        for file_path in self.project_path.glob(search_pattern):
            if any(part.startswith('.') for part in file_path.parts):
                continue
                
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        results.append({
                            "file": str(file_path.relative_to(self.project_path)),
                            "line": i,
                            "content": line.strip(),
                            "type": "pattern_match",
                            "relevance": 0.8
                        })
                        
                        if len(results) >= limit * 2:  # Get more than limit for sorting
                            break
                            
            except Exception:
                continue
        
        return results
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'matlab',
            '.jl': 'julia'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')
    
    def _analyze_python_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Analyze Python file structure using AST."""
        try:
            tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                        "docstring": ast.get_docstring(node)
                    })
                elif isinstance(node, ast.FunctionDef):
                    # Only top-level functions
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if node in getattr(parent, 'body', [])):
                        functions.append({
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "docstring": ast.get_docstring(node)
                        })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            return {
                "structure": {
                    "classes": classes,
                    "functions": functions,
                    "imports": imports
                }
            }
            
        except Exception as e:
            return {"structure": {"error": str(e)}}
    
    def _extract_focus_area(self, content: str, focus_area: str, language: str) -> str:
        """Extract specific area from content."""
        lines = content.splitlines()
        
        # Try to find the focus area
        start_line = None
        end_line = None
        indent_level = 0
        
        for i, line in enumerate(lines):
            if focus_area.lower() in line.lower():
                start_line = i
                # Detect indent level
                indent_level = len(line) - len(line.lstrip())
                
                # Find end of block
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if next_line.strip() and (len(next_line) - len(next_line.lstrip())) <= indent_level:
                        end_line = j
                        break
                else:
                    end_line = len(lines)
                break
        
        if start_line is not None:
            return '\n'.join(lines[start_line:end_line])
        else:
            return f"Focus area '{focus_area}' not found in file"
    
    def _get_line_context(self, content: str, line_num: int, context_lines: int = 2) -> str:
        """Get lines around a specific line number."""
        lines = content.splitlines()
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        
        context = []
        for i in range(start, end):
            prefix = ">>> " if i == line_num - 1 else "    "
            context.append(f"{prefix}{lines[i]}")
        
        return '\n'.join(context)
    
    def _extract_imports(self, file_path: Path) -> List[str]:
        """Extract imports from a Python file."""
        imports = []
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except Exception:
            # Fallback to regex
            try:
                content = file_path.read_text()
                import_lines = re.findall(r'^(?:from|import)\s+([^\s]+)', content, re.MULTILINE)
                imports.extend(import_lines)
            except Exception:
                pass
        
        return list(set(imports))
    
    def _find_importers(self, target_file: str) -> List[Dict[str, str]]:
        """Find files that import the target file."""
        importers = []
        
        # Convert file path to module name
        module_name = target_file.replace('.py', '').replace('/', '.')
        
        for py_file in self.project_path.rglob("*.py"):
            if str(py_file.relative_to(self.project_path)) == target_file:
                continue
                
            try:
                content = py_file.read_text()
                if module_name in content or target_file.replace('.py', '') in content:
                    # More precise check
                    for line_num, line in enumerate(content.splitlines(), 1):
                        if re.search(rf'(?:from|import).*{module_name}', line):
                            importers.append({
                                "file": str(py_file.relative_to(self.project_path)),
                                "line": line_num,
                                "import_statement": line.strip()
                            })
                            break
                            
            except Exception:
                continue
        
        return importers
    
    def _build_dependency_tree(self, file_path: str, depth: int, current_depth: int = 0) -> Dict[str, Any]:
        """Build dependency tree recursively."""
        if current_depth >= depth:
            return {"file": file_path, "dependencies": []}
        
        tree = {
            "file": file_path,
            "dependencies": []
        }
        
        full_path = self.project_path / file_path
        if full_path.exists() and full_path.suffix == '.py':
            imports = self._extract_imports(full_path)
            
            for imp in imports[:5]:  # Limit to prevent explosion
                import_path = self._import_to_path(imp)
                if import_path and (self.project_path / import_path).exists():
                    subtree = self._build_dependency_tree(import_path, depth, current_depth + 1)
                    tree["dependencies"].append(subtree)
        
        return tree
    
    def _import_to_path(self, import_name: str) -> Optional[str]:
        """Convert import name to file path."""
        # Handle relative imports and package imports
        parts = import_name.split('.')
        
        # Try as module
        module_path = '/'.join(parts) + '.py'
        if (self.project_path / module_path).exists():
            return module_path
        
        # Try as package
        package_path = '/'.join(parts) + '/__init__.py'
        if (self.project_path / package_path).exists():
            return package_path
        
        # Try without last part (might be importing from a module)
        if len(parts) > 1:
            module_path = '/'.join(parts[:-1]) + '.py'
            if (self.project_path / module_path).exists():
                return module_path
        
        return None
    
    def _analyze_file_component(self, file_path: Path) -> ComponentInfo:
        """Analyze a single file component."""
        try:
            content = file_path.read_text()
            lines = content.splitlines()
            
            imports = self._extract_imports(file_path)
            exports = []
            
            # For Python files, find exported symbols
            if file_path.suffix == '.py':
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                        if not node.name.startswith('_'):
                            exports.append(node.name)
            
            # Simple complexity calculation
            complexity = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            
            return ComponentInfo(
                path=str(file_path.relative_to(self.project_path)),
                type="file",
                name=file_path.stem,
                description=f"Python module with {len(exports)} exports",
                imports=imports,
                exports=exports,
                dependencies=[],
                complexity=complexity,
                loc=len(lines)
            )
            
        except Exception as e:
            return ComponentInfo(
                path=str(file_path.relative_to(self.project_path)),
                type="file",
                name=file_path.stem,
                description=f"Error analyzing file: {str(e)}",
                imports=[],
                exports=[],
                dependencies=[],
                complexity=0,
                loc=0
            )
    
    def _analyze_directory_component(self, dir_path: Path) -> List[ComponentInfo]:
        """Analyze all files in a directory component."""
        components = []
        
        for py_file in dir_path.rglob("*.py"):
            if not any(part.startswith('.') for part in py_file.parts):
                component = self._analyze_file_component(py_file)
                components.append(component)
        
        return components
    
    def _get_component_recommendations(self, components: List[ComponentInfo]) -> List[str]:
        """Get recommendations based on component analysis."""
        recommendations = []
        
        # Check complexity
        high_complexity = [c for c in components if c.complexity > 200]
        if high_complexity:
            recommendations.append(f"Consider refactoring {len(high_complexity)} files with high complexity")
        
        # Check dependencies
        high_deps = [c for c in components if len(c.imports) > 20]
        if high_deps:
            recommendations.append(f"{len(high_deps)} files have many dependencies - consider reducing coupling")
        
        return recommendations
    
    def _calculate_relationship_metrics(self, relationships: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics from relationship data."""
        nodes = relationships["nodes"]
        edges = relationships["edges"]
        
        # Calculate in-degree and out-degree
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        
        for edge in edges:
            out_degree[edge["from"]] += 1
            in_degree[edge["to"]] += 1
        
        # Find hubs and sinks
        hubs = [node for node, degree in out_degree.items() if degree > 5]
        sinks = [node for node in nodes if in_degree[node] > 5]
        
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "avg_dependencies": sum(out_degree.values()) / len(nodes) if nodes else 0,
            "hubs": hubs,
            "sinks": sinks,
            "max_out_degree": max(out_degree.values()) if out_degree else 0,
            "max_in_degree": max(in_degree.values()) if in_degree else 0
        }
    
    def _detect_mvc_pattern(self) -> Optional[Dict[str, Any]]:
        """Detect MVC/MVP/MVVM patterns."""
        # Look for common MVC directories
        patterns = {
            "mvc": ["models", "views", "controllers"],
            "mvp": ["models", "views", "presenters"],
            "mvvm": ["models", "views", "viewmodels"]
        }
        
        for pattern_name, dirs in patterns.items():
            found_dirs = []
            for dir_name in dirs:
                if any(self.project_path.glob(f"**/{dir_name}")):
                    found_dirs.append(dir_name)
            
            if len(found_dirs) >= 2:
                return {
                    "pattern": pattern_name.upper(),
                    "confidence": len(found_dirs) / len(dirs),
                    "found_components": found_dirs,
                    "description": f"{pattern_name.upper()} architectural pattern detected"
                }
        
        return None
    
    def _detect_layered_architecture(self) -> Optional[Dict[str, Any]]:
        """Detect layered architecture."""
        layers = {
            "presentation": ["ui", "views", "controllers", "routes", "api"],
            "business": ["services", "business", "domain", "use_cases"],
            "data": ["models", "repositories", "dao", "database", "db"]
        }
        
        found_layers = {}
        for layer_name, indicators in layers.items():
            for indicator in indicators:
                if list(self.project_path.glob(f"**/{indicator}")):
                    found_layers[layer_name] = indicator
                    break
        
        if len(found_layers) >= 2:
            return {
                "pattern": "Layered Architecture",
                "layers": found_layers,
                "confidence": len(found_layers) / len(layers),
                "description": "Layered architectural pattern with clear separation of concerns"
            }
        
        return None
    
    def _detect_singleton_pattern(self) -> List[Dict[str, Any]]:
        """Detect singleton pattern usage."""
        singletons = []
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                
                # Look for singleton patterns
                if "__new__" in content and "_instance" in content:
                    singletons.append({
                        "pattern": "Singleton",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 0.9,
                        "implementation": "Classic singleton with __new__"
                    })
                elif "@singleton" in content:
                    singletons.append({
                        "pattern": "Singleton",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 1.0,
                        "implementation": "Decorator-based singleton"
                    })
                    
            except Exception:
                continue
        
        return singletons
    
    def _detect_factory_pattern(self) -> List[Dict[str, Any]]:
        """Detect factory pattern usage."""
        factories = []
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                file_name = py_file.name.lower()
                content = py_file.read_text().lower()
                
                if "factory" in file_name or ("create" in content and "class" in content):
                    factories.append({
                        "pattern": "Factory",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 0.8 if "factory" in file_name else 0.6,
                        "type": "Factory Method" if "method" in content else "Abstract Factory"
                    })
                    
            except Exception:
                continue
        
        return factories
    
    def _detect_decorator_pattern(self) -> List[Dict[str, Any]]:
        """Detect decorator pattern usage."""
        decorators = []
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                
                # Count decorator usage
                decorator_count = len(re.findall(r'@\w+', content))
                custom_decorators = len(re.findall(r'def\s+\w+\(.*\):\s*def\s+\w+\(', content))
                
                if custom_decorators > 0:
                    decorators.append({
                        "pattern": "Decorator",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 0.9,
                        "custom_decorators": custom_decorators,
                        "total_decorator_usage": decorator_count
                    })
                    
            except Exception:
                continue
        
        return decorators
    
    def _detect_adapter_pattern(self) -> List[Dict[str, Any]]:
        """Detect adapter pattern usage."""
        adapters = []
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                file_name = py_file.name.lower()
                
                if "adapter" in file_name or "wrapper" in file_name:
                    adapters.append({
                        "pattern": "Adapter",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 0.8,
                        "type": "Class Adapter" if "adapter" in file_name else "Object Adapter"
                    })
                    
            except Exception:
                continue
        
        return adapters
    
    def _detect_observer_pattern(self) -> List[Dict[str, Any]]:
        """Detect observer pattern usage."""
        observers = []
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                
                # Look for observer/observable patterns
                if any(pattern in content for pattern in ["subscribe", "unsubscribe", "notify", "observer", "listener"]):
                    observers.append({
                        "pattern": "Observer",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 0.7,
                        "implementation": "Event-based" if "event" in content.lower() else "Classic Observer"
                    })
                    
            except Exception:
                continue
        
        return observers
    
    def _detect_strategy_pattern(self) -> List[Dict[str, Any]]:
        """Detect strategy pattern usage."""
        strategies = []
        
        for py_file in self.project_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                file_name = py_file.name.lower()
                
                if "strategy" in file_name or "policy" in file_name:
                    strategies.append({
                        "pattern": "Strategy",
                        "file": str(py_file.relative_to(self.project_path)),
                        "confidence": 0.8,
                        "type": "Strategy Pattern"
                    })
                    
            except Exception:
                continue
        
        return strategies
    
    def _analyze_languages(self) -> Dict[str, int]:
        """Analyze programming language distribution."""
        language_stats = defaultdict(int)
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                language = self._detect_language(str(file_path))
                if language != 'text':
                    language_stats[language] += 1
        
        return dict(language_stats)
    
    def _parse_requirements(self) -> List[str]:
        """Parse requirements.txt file."""
        libs = []
        req_file = self.project_path / "requirements.txt"
        
        try:
            content = req_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name
                    pkg = re.split(r'[<>=!]', line)[0].strip()
                    if pkg:
                        libs.append(pkg)
        except Exception:
            pass
        
        return libs
    
    def _parse_package_json(self) -> Dict[str, List[str]]:
        """Parse package.json file."""
        result = {"dependencies": [], "devDependencies": []}
        
        try:
            pkg_file = self.project_path / "package.json"
            data = json.loads(pkg_file.read_text())
            
            if "dependencies" in data:
                result["dependencies"] = list(data["dependencies"].keys())
            
            if "devDependencies" in data:
                result["devDependencies"] = list(data["devDependencies"].keys())
                
        except Exception:
            pass
        
        return result
    
    def _parse_pipfile(self) -> List[str]:
        """Parse Pipfile."""
        libs = []
        
        try:
            pipfile = self.project_path / "Pipfile"
            content = pipfile.read_text()
            
            # Simple parsing - look for [packages] section
            in_packages = False
            for line in content.splitlines():
                if "[packages]" in line:
                    in_packages = True
                elif line.startswith("[") and in_packages:
                    break
                elif in_packages and "=" in line:
                    pkg = line.split("=")[0].strip()
                    if pkg:
                        libs.append(pkg)
                        
        except Exception:
            pass
        
        return libs
    
    def _detect_frameworks(self) -> List[Dict[str, str]]:
        """Detect web frameworks and other frameworks."""
        frameworks = []
        
        # Framework indicators
        indicators = {
            "django": ["manage.py", "settings.py", "urls.py"],
            "flask": ["app.py", "flask", "Flask"],
            "fastapi": ["fastapi", "FastAPI"],
            "pyramid": ["pyramid", "development.ini"],
            "tornado": ["tornado", "RequestHandler"],
            "react": ["package.json", "react", "jsx"],
            "angular": ["angular.json", "@angular"],
            "vue": ["vue.config.js", "vue"],
            "express": ["express", "app.listen"],
            "rails": ["Gemfile", "rails"],
            "spring": ["pom.xml", "springframework"]
        }
        
        for framework, signs in indicators.items():
            confidence = 0
            for sign in signs:
                # Check files
                if list(self.project_path.glob(f"**/{sign}")):
                    confidence += 0.4
                
                # Check in requirements/package.json
                if framework in str(self._parse_requirements()) or framework in str(self._parse_package_json()):
                    confidence += 0.6
            
            if confidence > 0.5:
                frameworks.append({
                    "name": framework,
                    "confidence": min(confidence, 1.0),
                    "type": "web" if framework in ["django", "flask", "fastapi", "express"] else "frontend"
                })
        
        return frameworks
    
    def _detect_databases(self) -> List[Dict[str, str]]:
        """Detect database usage."""
        databases = []
        
        db_indicators = {
            "postgresql": ["psycopg2", "postgresql", "postgres"],
            "mysql": ["mysql", "pymysql", "mysqlclient"],
            "sqlite": ["sqlite3", "sqlite"],
            "mongodb": ["pymongo", "mongodb", "mongoose"],
            "redis": ["redis", "aioredis"],
            "elasticsearch": ["elasticsearch", "elastic"]
        }
        
        # Check requirements and code
        all_deps = str(self._parse_requirements()) + str(self._parse_package_json())
        
        for db, indicators in db_indicators.items():
            if any(ind in all_deps.lower() for ind in indicators):
                databases.append({
                    "type": db,
                    "confidence": 0.9
                })
        
        return databases
    
    def _detect_testing_frameworks(self) -> List[Dict[str, str]]:
        """Detect testing frameworks."""
        testing = []
        
        test_indicators = {
            "pytest": ["pytest", "test_*.py", "conftest.py"],
            "unittest": ["unittest", "TestCase"],
            "jest": ["jest", "test.js", "spec.js"],
            "mocha": ["mocha", "describe(", "it("],
            "jasmine": ["jasmine", "spec.js"],
            "rspec": ["rspec", "spec.rb"]
        }
        
        for framework, indicators in test_indicators.items():
            found = False
            
            # Check files and dependencies
            for indicator in indicators:
                if list(self.project_path.glob(f"**/{indicator}")) or indicator in str(self._parse_requirements()):
                    found = True
                    break
            
            if found:
                testing.append({
                    "framework": framework,
                    "has_tests": len(list(self.project_path.glob("**/test*"))) > 0
                })
        
        return testing
    
    def _get_tech_stack_recommendations(self, tech_stack: Dict[str, Any]) -> List[str]:
        """Get recommendations based on tech stack analysis."""
        recommendations = []
        
        # Check for testing
        if not tech_stack["testing"]:
            recommendations.append("Consider adding a testing framework (pytest for Python, jest for JavaScript)")
        
        # Check for linting/formatting
        if not any(tool in str(tech_stack["tools"]) for tool in ["eslint", "pylint", "flake8", "black"]):
            recommendations.append("Consider adding code quality tools (linters, formatters)")
        
        # Check for security tools
        if not any(tool in str(tech_stack["tools"]) for tool in ["bandit", "safety", "snyk"]):
            recommendations.append("Consider adding security scanning tools")
        
        return recommendations
    
    def _parse_setup_py_entries(self, setup_py: Path) -> List[Dict[str, str]]:
        """Parse entry points from setup.py."""
        entries = []
        
        try:
            content = setup_py.read_text()
            
            # Look for console_scripts
            if "console_scripts" in content:
                # Extract entry points
                matches = re.findall(r'"([^"]+)\s*=\s*([^"]+)"', content)
                for name, entry in matches:
                    entries.append({
                        "file": "setup.py",
                        "type": f"Console script: {name}",
                        "executable": True
                    })
                    
        except Exception:
            pass
        
        return entries
    
    def get_tool_definitions(self) -> list:
        """
        Get OpenAI-style function definitions for codebase tools.
        """
        return [
            {
                "name": "search_codebase",
                "description": "Search for code patterns, functions, classes, or concepts in the codebase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query or code pattern"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Optional file pattern to limit search (e.g., '*.py', 'src/**/*.js')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "explore_file",
                "description": "Read and analyze a specific file with optional focus on certain sections",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file relative to project root"
                        },
                        "focus_area": {
                            "type": "string",
                            "description": "Optional area to focus on (e.g., 'class UserAuth', 'function validate')"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "find_symbol",
                "description": "Find where a class, function, or variable is defined and used",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name of the symbol to find"
                        },
                        "symbol_type": {
                            "type": "string",
                            "enum": ["class", "function", "variable", "import"],
                            "description": "Optional type filter"
                        }
                    },
                    "required": ["symbol_name"]
                }
            },
            {
                "name": "trace_imports",
                "description": "Trace import dependencies for a file or module",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to analyze"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "analyze_component",
                "description": "Deep dive into a specific component or module structure",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "component_path": {
                            "type": "string",
                            "description": "Path to component directory or main file"
                        }
                    },
                    "required": ["component_path"]
                }
            },
            {
                "name": "map_relationships",
                "description": "Map relationships between components starting from an entry point",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entry_point": {
                            "type": "string",
                            "description": "Starting point for relationship mapping"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "How many levels deep to trace",
                            "default": 2
                        }
                    },
                    "required": ["entry_point"]
                }
            },
            {
                "name": "find_patterns",
                "description": "Identify design patterns and architectural patterns in the codebase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern_type": {
                            "type": "string",
                            "enum": ["all", "creational", "structural", "behavioral", "architectural"],
                            "description": "Type of pattern to find",
                            "default": "all"
                        }
                    }
                }
            },
            {
                "name": "assess_tech_stack",
                "description": "Identify technologies, frameworks, and libraries used in the project",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "find_entry_points",
                "description": "Locate application entry points and main execution paths",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "analyze_data_flow",
                "description": "Trace data flow through the application from an entry point",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entry_point": {
                            "type": "string",
                            "description": "Starting point for data flow analysis (file path or function name)"
                        }
                    },
                    "required": ["entry_point"]
                }
            }
        ]