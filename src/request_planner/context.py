"""
Context retrieval for the Request Planner.

This module handles searching and retrieving relevant code context
to help the planner make informed decisions.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .models import SearchResult


class ContextRetriever:
    """
    Retrieves relevant context from the codebase for planning.
    
    This is a simplified version that will be replaced with a full
    RAG service in the future.
    """
    
    def __init__(self, repo_path: Path):
        """Initialize the context retriever."""
        self.repo_path = repo_path
        self._ignored_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'env', '.env', 'dist', 'build', '.pytest_cache', '.mypy_cache'
        }
        self._code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
            '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php', '.swift'
        }
        
    def get_context(self, query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get relevant context for a query and intent.
        
        Args:
            query: The user's query
            intent: Parsed intent information
            
        Returns:
            Context information including relevant files and snippets
        """
        context = {
            "query": query,
            "intent": intent,
            "relevant_files": [],
            "snippets": []
        }
        
        # Search for relevant files
        search_results = self.search(query, limit=20)
        
        # Extract relevant files and enhanced snippets
        relevant_files = set()
        for result in search_results[:10]:  # Limit to top 10 for snippet extraction
            relevant_files.add(result.file)
            
            # Get snippet with radius
            snippet_info = self.get_snippet_with_radius(
                result.file, 
                result.line,
                radius=10  # Use smaller radius for multiple snippets
            )
            
            if snippet_info:
                context["snippets"].append({
                    "file": result.file,
                    "line": result.line,
                    "content": snippet_info["snippet_text"],
                    "context_type": snippet_info["context"]["type"],
                    "context_name": snippet_info["context"]["name"],
                    "start_line": snippet_info["start_line"],
                    "end_line": snippet_info["end_line"]
                })
            else:
                # Fallback to simple snippet
                context["snippets"].append({
                    "file": result.file,
                    "line": result.line,
                    "content": result.content
                })
        
        context["relevant_files"] = sorted(list(relevant_files))
        
        # Add intent-specific context
        if intent["type"] == "add_feature" and "target" in intent:
            # Look for similar features
            similar = self._find_similar_patterns(intent["target"])
            context["similar_features"] = similar
        
        return context
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search the codebase for a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        results = []
        
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        # Search files
        for file_path in self._iter_code_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.splitlines()
                
                for i, line in enumerate(lines, 1):
                    score = self._score_line(line, keywords)
                    if score > 0:
                        results.append(SearchResult(
                            file=str(file_path.relative_to(self.repo_path)),
                            line=i,
                            content=line.strip(),
                            score=score
                        ))
            except Exception:
                # Skip files that can't be read
                continue
        
        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get the content of a file."""
        full_path = self.repo_path / file_path
        if full_path.exists() and full_path.is_file():
            try:
                return full_path.read_text(encoding='utf-8')
            except Exception:
                return None
        return None
    
    def get_snippet_with_radius(
        self, 
        file_path: str, 
        line_number: int, 
        radius: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Get a code snippet with surrounding context (radius).
        
        Args:
            file_path: Path to the file
            line_number: Center line number (1-based)
            radius: Number of lines before and after to include
            
        Returns:
            Dictionary with snippet information or None if error
        """
        content = self.get_file_content(file_path)
        if not content:
            return None
        
        lines = content.splitlines()
        total_lines = len(lines)
        
        # Calculate bounds (convert to 0-based)
        start_idx = max(0, line_number - 1 - radius)
        end_idx = min(total_lines, line_number + radius)
        
        # Extract snippet lines
        snippet_lines = []
        for i in range(start_idx, end_idx):
            snippet_lines.append({
                "number": i + 1,
                "content": lines[i],
                "is_target": (i + 1 == line_number)
            })
        
        # Detect context (function/class this line belongs to)
        context_info = self._detect_code_context(lines, line_number - 1)
        
        return {
            "file": file_path,
            "target_line": line_number,
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "radius": radius,
            "lines": snippet_lines,
            "context": context_info,
            "snippet_text": "\n".join(line["content"] for line in snippet_lines)
        }
    
    def _detect_code_context(
        self, 
        lines: List[str], 
        target_idx: int
    ) -> Dict[str, Any]:
        """
        Detect the code context (function/class) for a given line.
        
        Args:
            lines: All lines in the file
            target_idx: Target line index (0-based)
            
        Returns:
            Context information
        """
        context = {
            "type": None,
            "name": None,
            "start_line": None
        }
        
        # Search backwards for containing function/class
        indent_level = len(lines[target_idx]) - len(lines[target_idx].lstrip())
        
        for i in range(target_idx, -1, -1):
            line = lines[i]
            line_indent = len(line) - len(line.lstrip())
            
            # Look for definitions at lower indent level
            if line_indent < indent_level:
                # Check for function definition
                func_match = re.match(r'\s*(def|async def)\s+(\w+)', line)
                if func_match:
                    context["type"] = "function"
                    context["name"] = func_match.group(2)
                    context["start_line"] = i + 1
                    break
                
                # Check for class definition
                class_match = re.match(r'\s*class\s+(\w+)', line)
                if class_match:
                    context["type"] = "class"
                    context["name"] = class_match.group(1)
                    context["start_line"] = i + 1
                    break
        
        return context
    
    def _iter_code_files(self):
        """Iterate over code files in the repository."""
        for root, dirs, files in os.walk(self.repo_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in self._ignored_dirs]
            
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                if file_path.suffix in self._code_extensions:
                    yield file_path
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from a query."""
        # Simple keyword extraction
        # Remove common words and split
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
            'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Split into words and filter
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Also look for camelCase and snake_case identifiers
        identifiers = re.findall(r'[a-zA-Z_]\w*', query)
        keywords.extend(identifiers)
        
        return list(set(keywords))
    
    def _score_line(self, line: str, keywords: List[str]) -> float:
        """Score a line based on keyword matches."""
        if not line.strip():
            return 0.0
        
        line_lower = line.lower()
        score = 0.0
        
        for keyword in keywords:
            if keyword.lower() in line_lower:
                score += 1.0
                # Bonus for exact word match
                if re.search(r'\b' + re.escape(keyword) + r'\b', line, re.I):
                    score += 0.5
        
        # Bonus for function/class definitions
        if re.match(r'\s*(def|class|function|const|let|var)\s+', line):
            score += 0.5
        
        return score
    
    def _find_similar_patterns(self, target: str) -> List[Dict[str, Any]]:
        """Find similar code patterns to a target."""
        patterns = []
        
        # Look for similar function/class names
        target_words = re.findall(r'\w+', target.lower())
        
        for file_path in self._iter_code_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Look for similar definitions
                for match in re.finditer(r'(def|class|function)\s+(\w+)', content):
                    name = match.group(2)
                    name_words = re.findall(r'\w+', name.lower())
                    
                    # Check similarity
                    common_words = set(target_words) & set(name_words)
                    if common_words:
                        patterns.append({
                            "file": str(file_path.relative_to(self.repo_path)),
                            "name": name,
                            "type": match.group(1),
                            "similarity": len(common_words) / len(target_words)
                        })
            except Exception:
                continue
        
        # Sort by similarity
        patterns.sort(key=lambda p: p["similarity"], reverse=True)
        return patterns[:5]