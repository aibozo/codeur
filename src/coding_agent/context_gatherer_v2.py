"""
Improved context gatherer that properly uses RAG for intelligent chunk selection.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..proto_gen import messages_pb2
from .models import CodeContext
from ..core.path_utils import normalize_repo_path

logger = logging.getLogger(__name__)


class SmartContextGatherer:
    """
    Gathers context using RAG to find semantically relevant chunks.
    
    Key improvements:
    1. Uses RAG search to find relevant chunks with line numbers
    2. Preserves full chunk content (no truncation)
    3. Allows agents to request additional context
    """
    
    def __init__(self, repo_path: str, rag_client=None):
        """
        Initialize the context gatherer.
        
        Args:
            repo_path: Path to repository
            rag_client: RAG client for search
        """
        self.repo_path = Path(repo_path)
        self.rag_client = rag_client
        self.rag_enabled = rag_client is not None

        logger.info(f"SmartContextGatherer initialized - RAG: {self.rag_enabled}")

    def _norm(self, path: str) -> str:
        return normalize_repo_path(path, self.repo_path)
    
    def gather_context(
        self, 
        task: messages_pb2.CodingTask,
        max_chunks: int = 10,
        context_tokens: int = 4000
    ) -> CodeContext:
        """
        Gather context for a coding task using semantic search.
        
        Args:
            task: The coding task
            max_chunks: Maximum number of chunks to include
            context_tokens: Token budget for context
            
        Returns:
            CodeContext with relevant chunks
        """
        context = CodeContext(
            task_goal=task.goal,
            file_paths=list(task.paths),
            skeleton_patches=list(task.skeleton_patch)
        )
        
        if not self.rag_enabled:
            logger.warning("RAG not enabled, falling back to basic file loading")
            self._load_full_files(task.paths, context)
            return context
        
        # 1. Search for semantically relevant chunks based on task goal
        logger.info(f"Searching for chunks relevant to: {task.goal}")
        
        try:
            # Primary search based on task goal
            goal_results = self.rag_client.search(
                query=task.goal,
                k=max_chunks,
                filters={}  # No filters to get most relevant chunks
            )
            
            # Add chunks with preserved line numbers
            for result in goal_results:
                chunk = result.get("chunk", {})
                file_path = chunk.get("file_path", "")
                start_line = chunk.get("start_line", 0)
                end_line = chunk.get("end_line", 0)
                content = chunk.get("content", "")
                
                # Format with line numbers
                if content and start_line > 0:
                    numbered_content = self._add_line_numbers(content, start_line)
                    
                    # Add as a chunk with metadata
                    chunk_key = f"{file_path}:{start_line}-{end_line}"
                    context.add_blob(chunk_key, numbered_content)
                    
                    logger.debug(f"Added chunk: {chunk_key} ({len(content)} chars)")
            
            # 2. Get specific file chunks if paths are mentioned
            for file_path in task.paths[:3]:  # Limit to first 3 files
                norm_path = self._norm(file_path)
                file_results = self.rag_client.search(
                    query=f"{task.goal} in {norm_path}",
                    k=3,  # Get top 3 chunks per file
                    filters={"file_path": norm_path}
                )
                
                for result in file_results:
                    chunk = result.get("chunk", {})
                    start_line = chunk.get("start_line", 0)
                    end_line = chunk.get("end_line", 0)
                    content = chunk.get("content", "")
                    
                    if content and start_line > 0:
                        numbered_content = self._add_line_numbers(content, start_line)
                        chunk_key = f"{file_path}:{start_line}-{end_line}"
                        
                        # Avoid duplicates
                        if chunk_key not in context.blob_contents:
                            context.add_blob(chunk_key, numbered_content)
            
            # 3. Load skeleton of mentioned files for structure
            for path in task.paths[:2]:  # First 2 files
                self._load_file_skeleton(path, context)
            
            # 4. Find related functions/classes
            self._find_related_symbols(task, context)
            
            # 5. Estimate tokens and log
            context.token_count = self._estimate_tokens(context)
            logger.info(f"Gathered context: {context.token_count} tokens, "
                       f"{len(context.blob_contents)} chunks, "
                       f"{len(context.file_snippets)} file skeletons")
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}, falling back to file loading")
            self._load_full_files(task.paths, context)
        
        return context
    
    def _add_line_numbers(self, content: str, start_line: int) -> str:
        """Add line numbers to content."""
        lines = content.split('\n')
        numbered_lines = []
        
        for i, line in enumerate(lines):
            line_num = start_line + i
            numbered_lines.append(f"{line_num:4d}: {line}")
        
        return '\n'.join(numbered_lines)
    
    def _load_file_skeleton(self, file_path: str, context: CodeContext):
        """Load file skeleton (imports, class/function signatures)."""
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return
        
        try:
            content = full_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            skeleton_lines = []
            in_function = False
            indent_level = 0
            
            for i, line in enumerate(lines):
                # Always include imports
                if line.strip().startswith(('import ', 'from ')):
                    skeleton_lines.append((i + 1, line))
                
                # Include class definitions
                elif line.strip().startswith('class '):
                    skeleton_lines.append((i + 1, line))
                    indent_level = len(line) - len(line.lstrip())
                
                # Include function/method signatures
                elif line.strip().startswith('def '):
                    skeleton_lines.append((i + 1, line))
                    # Include docstring if present
                    if i + 1 < len(lines) and '"""' in lines[i + 1]:
                        skeleton_lines.append((i + 2, lines[i + 1]))
                        # Find end of docstring
                        for j in range(i + 2, min(i + 10, len(lines))):
                            skeleton_lines.append((j + 1, lines[j]))
                            if '"""' in lines[j] and j > i + 1:
                                break
            
            # Format skeleton with line numbers
            if skeleton_lines:
                skeleton_content = '\n'.join(
                    f"{num:4d}: {line}" for num, line in skeleton_lines
                )
                context.add_snippet(f"{file_path} (skeleton)", skeleton_content)
                
        except Exception as e:
            logger.warning(f"Failed to load skeleton for {file_path}: {e}")
    
    def _find_related_symbols(self, task: messages_pb2.CodingTask, context: CodeContext):
        """Find related functions/classes."""
        if not self.rag_enabled:
            return
        
        try:
            # Search for related symbols
            results = self.rag_client.search(
                query=task.goal,
                k=5,
                filters={"chunk_type": {"$in": ["function", "method", "class"]}}
            )
            
            for result in results:
                chunk = result.get("chunk", {})
                related = {
                    "file": chunk.get("file_path", ""),
                    "line": chunk.get("start_line", 0),
                    "symbol": chunk.get("symbol_name", ""),
                    "type": chunk.get("chunk_type", ""),
                    "score": result.get("score", 0.0)
                }
                context.related_functions.append(related)
                
        except Exception as e:
            logger.warning(f"Failed to find related symbols: {e}")
    
    def _load_full_files(self, paths: List[str], context: CodeContext):
        """Fallback: Load full files with line numbers."""
        for path in paths[:3]:  # Limit to 3 files
            file_path = self.repo_path / path
            
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    numbered_content = self._add_line_numbers(content, 1)
                    context.add_snippet(path, numbered_content)
                    logger.debug(f"Loaded full file: {path}")
                except Exception as e:
                    logger.warning(f"Failed to load file {path}: {e}")
    
    def _estimate_tokens(self, context: CodeContext) -> int:
        """Estimate token count."""
        total_chars = 0
        
        for content in context.file_snippets.values():
            total_chars += len(content)
        
        for content in context.blob_contents.values():
            total_chars += len(content)
        
        # Rough estimate: ~4 chars per token
        return total_chars // 4