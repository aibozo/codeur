"""
Context gathering for Coding Agent with RAG integration.

Responsible for:
- Fetching blob contents from RAG service
- Finding related code snippets
- Gathering imports and dependencies
- Building comprehensive context for patch generation
"""

import logging
from typing import List, Dict, Optional, Set
from pathlib import Path
import re

from ..rag_service import RAGClient
from ..proto_gen import messages_pb2
from ..core.path_utils import normalize_repo_path
from .models import CodeContext

logger = logging.getLogger(__name__)


class ContextGatherer:
    """
    Gathers relevant context for code generation using RAG service.
    """
    
    def __init__(self, repo_path: str, rag_client: Optional[RAGClient] = None):
        """
        Initialize context gatherer.
        
        Args:
            repo_path: Path to the repository
            rag_client: Optional RAG client (creates one if not provided)
        """
        self.repo_path = Path(repo_path)
        
        # Initialize RAG client
        if rag_client:
            self.rag_client = rag_client
            self.rag_enabled = True
        else:
            try:
                from ..rag_service import RAGService
                rag_dir = self.repo_path / ".rag"
                rag_service = RAGService(
                    persist_directory=str(rag_dir), repo_path=str(self.repo_path)
                )
                self.rag_client = RAGClient(service=rag_service)
                self.rag_enabled = self.rag_client.is_available()
                
                if self.rag_enabled:
                    logger.info("RAG client initialized for context gathering")
                else:
                    logger.warning("RAG client created but not available")
            except Exception as e:
                logger.error(f"Failed to initialize RAG client: {e}")
                self.rag_client = None
                self.rag_enabled = False

    def _norm(self, path: str) -> str:
        """Normalize a path relative to the repository."""
        return normalize_repo_path(path, self.repo_path)
    
    def gather_context(
        self,
        task: messages_pb2.CodingTask,
        context_tokens: int = 3000
    ) -> CodeContext:
        """
        Gather all relevant context for a coding task.
        
        Args:
            task: The coding task
            context_tokens: Maximum context tokens
            
        Returns:
            CodeContext with all gathered information
        """
        context = CodeContext(task_goal=task.goal)
        
        # Add skeleton patches from task
        context.skeleton_patches.extend(task.skeleton_patch)
        
        # 1. Fetch blob contents if available
        if self.rag_enabled and task.blob_ids:
            self._fetch_blob_contents(task.blob_ids, context)
        
        # 2. Load file contents for affected paths
        self._load_file_snippets(task.paths, context)
        
        # 3. Find related functions and imports
        if self.rag_enabled:
            self._find_related_code(task, context)
            self._gather_imports(task.paths, context)
        
        # 4. Find error handling patterns if relevant
        if "error" in task.goal.lower() or "exception" in task.goal.lower():
            self._find_error_patterns(context)
        
        # 5. Estimate token count
        context.token_count = self._estimate_tokens(context)
        
        # 6. Trim if over budget
        if context.token_count > context_tokens:
            self._trim_context(context, context_tokens)
        
        logger.info(f"Gathered context: {context.token_count} tokens, "
                   f"{len(context.file_snippets)} files, "
                   f"{len(context.blob_contents)} blobs")
        
        return context
    
    def _fetch_blob_contents(self, blob_ids: List[str], context: CodeContext):
        """Fetch content for blob IDs."""
        for blob_id in blob_ids[:5]:  # Limit to 5 blobs
            try:
                # Parse blob ID format: file_path:start_line:end_line:hash
                parts = blob_id.split(':')
                if len(parts) >= 3:
                    file_path = parts[0]
                    start_line = int(parts[1])
                    end_line = int(parts[2]) if len(parts) > 2 else start_line
                    
                    # Get snippet from RAG
                    snippet = self.rag_client.get_snippet(
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        context_lines=5
                    )
                    
                    if snippet:
                        context.add_blob(blob_id, snippet)
                        logger.debug(f"Fetched blob: {blob_id} ({len(snippet)} chars)")
                        
            except Exception as e:
                logger.warning(f"Failed to fetch blob {blob_id}: {e}")
    
    def _load_file_snippets(self, paths: List[str], context: CodeContext):
        """Load snippets from affected files."""
        for path in paths[:5]:  # Limit to 5 files
            file_path = self.repo_path / path
            
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Include line numbers for better patch generation
                    lines = content.split('\n')[:500]
                    numbered_lines = []
                    for i, line in enumerate(lines, start=1):
                        # Format: "line_number: content"
                        numbered_lines.append(f"{i:4d}: {line}")
                    
                    snippet = '\n'.join(numbered_lines)
                    
                    context.add_snippet(path, snippet)
                    logger.debug(f"Loaded file snippet with line numbers: {path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load file {path}: {e}")
    
    def _find_related_code(self, task: messages_pb2.CodingTask, context: CodeContext):
        """Find related functions using RAG search."""
        if not self.rag_enabled:
            return
        
        try:
            # Search for related code
            results = self.rag_client.search(
                query=task.goal,
                k=5,
                filters={"chunk_type": {"$in": ["function", "method", "class"]}}
            )
            
            for result in results:
                related = {
                    "file": result.get("file_path", ""),
                    "line": result.get("start_line", 0),
                    "symbol": result.get("symbol_name", ""),
                    "type": result.get("chunk_type", ""),
                    "score": result.get("score", 0.0)
                }
                context.related_functions.append(related)
                
            logger.debug(f"Found {len(results)} related functions")
            
        except Exception as e:
            logger.warning(f"Failed to find related code: {e}")
    
    def _gather_imports(self, paths: List[str], context: CodeContext):
        """Gather import statements from files."""
        if not self.rag_enabled:
            return
        
        import_pattern = r'^(from\s+\S+\s+import|import\s+)'
        
        for path in paths:
            norm_path = self._norm(path)
            try:
                # Use RAG to find imports
                results = self.rag_client.search(
                    query=f"import statements in {norm_path}",
                    k=10,
                    filters={"file_path": norm_path}
                )
                
                # Extract unique imports
                imports = set()
                for result in results:
                    content = result.get("content", "")
                    for line in content.split('\n'):
                        if re.match(import_pattern, line.strip()):
                            imports.add(line.strip())
                
                context.imports.extend(list(imports))
                
            except Exception as e:
                logger.warning(f"Failed to gather imports from {path}: {e}")
    
    def _find_error_patterns(self, context: CodeContext):
        """Find error handling patterns in the codebase."""
        if not self.rag_enabled:
            return
        
        try:
            # Search for error handling examples
            results = self.rag_client.search(
                query="error handling try except exception",
                k=3
            )
            
            patterns = []
            for result in results:
                content = result.get("content", "")
                if "try:" in content or "except" in content:
                    patterns.append(content[:200])  # Take snippet
            
            context.error_patterns = patterns
            logger.debug(f"Found {len(patterns)} error handling patterns")
            
        except Exception as e:
            logger.warning(f"Failed to find error patterns: {e}")
    
    def _estimate_tokens(self, context: CodeContext) -> int:
        """Estimate token count for context."""
        # Simple estimation: 1 token H 4 characters
        total_chars = 0
        
        # Count goal
        total_chars += len(context.task_goal)
        
        # Count file snippets
        for content in context.file_snippets.values():
            total_chars += len(content)
        
        # Count blob contents
        for content in context.blob_contents.values():
            total_chars += len(content)
        
        # Count other fields
        total_chars += sum(len(imp) for imp in context.imports)
        total_chars += sum(len(str(func)) for func in context.related_functions)
        total_chars += sum(len(pattern) for pattern in context.error_patterns)
        total_chars += sum(len(patch) for patch in context.skeleton_patches)
        
        return total_chars // 4
    
    def _trim_context(self, context: CodeContext, max_tokens: int):
        """Trim context to fit within token budget."""
        logger.info(f"Trimming context from {context.token_count} to {max_tokens} tokens")
        
        # Priority order: skeleton_patches > file_snippets > blob_contents > related > imports > error_patterns
        
        # Trim error patterns first
        while context.error_patterns and context.token_count > max_tokens:
            context.error_patterns.pop()
            context.token_count = self._estimate_tokens(context)
        
        # Trim imports
        while len(context.imports) > 10 and context.token_count > max_tokens:
            context.imports.pop()
            context.token_count = self._estimate_tokens(context)
        
        # Trim related functions
        while len(context.related_functions) > 3 and context.token_count > max_tokens:
            context.related_functions.pop()
            context.token_count = self._estimate_tokens(context)
        
        # Trim blob contents
        while len(context.blob_contents) > 2 and context.token_count > max_tokens:
            # Remove the largest blob
            largest_blob = max(context.blob_contents.keys(), 
                             key=lambda k: len(context.blob_contents[k]))
            del context.blob_contents[largest_blob]
            context.token_count = self._estimate_tokens(context)
        
        # Trim file snippets last (most important)
        for file_path in list(context.file_snippets.keys()):
            if context.token_count <= max_tokens:
                break
            
            # Trim content by half
            content = context.file_snippets[file_path]
            context.file_snippets[file_path] = content[:len(content)//2]
            context.token_count = self._estimate_tokens(context)
        
        logger.info(f"Trimmed context to {context.token_count} tokens")