"""
RAG integration for Code Planner.

This module handles:
- Prefetching relevant code blobs for tasks
- Enhancing task context with semantic search
- Providing code snippets for skeleton patches
"""

import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from ..rag_service import RAGClient, RAGService
from ..proto_gen import messages_pb2
from ..core.path_utils import normalize_repo_path

logger = logging.getLogger(__name__)


class CodePlannerRAGIntegration:
    """
    RAG integration for the Code Planner.
    
    Provides intelligent code retrieval and context prefetching
    for generating better CodingTasks.
    """
    
    def __init__(self, repo_path: str, rag_client: Optional[RAGClient] = None):
        """
        Initialize RAG integration.
        
        Args:
            repo_path: Path to the repository
            rag_client: Optional RAG client (creates one if not provided)
        """
        self.repo_path = Path(repo_path)
        
        if rag_client:
            self.rag_client = rag_client
            try:
                self.enabled = self.rag_client.is_available()
            except Exception:
                self.enabled = False
        else:
            # Create RAG client with repo-specific persistence
            try:
                rag_dir = self.repo_path / ".rag"
                rag_service = RAGService(
                    persist_directory=str(rag_dir), repo_path=str(self.repo_path)
                )
                self.rag_client = RAGClient(service=rag_service)
                
                # Check if available
                if not self.rag_client.is_available():
                    logger.warning("RAG client created but embeddings not available")
                    self.enabled = False
                else:
                    self.enabled = True
                    logger.info("RAG integration initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG integration: {e}")
                self.rag_client = None
                self.enabled = False

    def _norm(self, path: str) -> str:
        """Normalize a path relative to the repository."""
        return normalize_repo_path(path, self.repo_path)
    
    def prefetch_blobs_for_step(
        self, 
        step: messages_pb2.Step,
        affected_files: List[str],
        k: int = 10
    ) -> List[str]:
        """
        Prefetch relevant code blobs for a step.
        
        Args:
            step: The plan step
            affected_files: Files affected by this step
            k: Number of blobs to retrieve
            
        Returns:
            List of blob IDs for relevant code chunks
        """
        if not self.enabled:
            return []
        
        blob_ids = []
        
        try:
            # Build search query from step goal and hints
            query_parts = [step.goal]
            query_parts.extend(step.hints[:3])  # Use first 3 hints
            query = " ".join(query_parts)
            
            # Add file filters if we have affected files
            filters = {}
            if affected_files:
                norm_files = [self._norm(p) for p in affected_files]
                filters["file_path"] = {"$in": norm_files}
            
            # Search for relevant code
            results = self.rag_client.search(
                query=query,
                k=k,
                filters=filters
            )
            
            # Extract blob IDs from results
            for result in results:
                # Create a blob ID from file path and chunk info
                blob_id = self._create_blob_id(result)
                if blob_id:
                    blob_ids.append(blob_id)
            
            logger.debug(f"Prefetched {len(blob_ids)} blobs for step: {step.goal[:50]}...")
            
        except Exception as e:
            logger.error(f"Error prefetching blobs: {e}")
        
        return blob_ids
    
    def get_context_for_task(
        self,
        task: messages_pb2.CodingTask,
        max_tokens: int = 2000
    ) -> str:
        """
        Get relevant context for a coding task.
        
        Args:
            task: The coding task
            max_tokens: Maximum tokens to return
            
        Returns:
            Formatted context string
        """
        if not self.enabled:
            return ""
        
        try:
            # Build query from task goal
            query = task.goal
            
            # Add file filters
            filters = {}
            if task.paths:
                norm_paths = [self._norm(p) for p in task.paths]
                filters["file_path"] = {"$in": norm_paths}
            
            # Get context
            context = self.rag_client.get_context(
                query=query,
                k=8,
                max_tokens=max_tokens
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for task: {e}")
            return ""
    
    def find_similar_implementations(
        self,
        function_name: str,
        implementation_type: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar implementations to help with skeleton generation.
        
        Args:
            function_name: Name of the function/class
            implementation_type: Type of implementation (e.g., "error_handler", "validator")
            k: Number of examples to find
            
        Returns:
            List of similar implementations
        """
        if not self.enabled:
            return []
        
        try:
            # Search for similar implementations
            query = f"{implementation_type} {function_name} implementation example"
            
            results = self.rag_client.search(
                query=query,
                k=k,
                filters={"chunk_type": {"$in": ["function", "method", "class"]}}
            )
            
            # Format results
            implementations = []
            for result in results:
                impl = {
                    "file": result["file_path"],
                    "line": result["start_line"],
                    "symbol": result.get("symbol_name", ""),
                    "type": result.get("chunk_type", ""),
                    "snippet": self._get_snippet_for_result(result)
                }
                implementations.append(impl)
            
            return implementations
            
        except Exception as e:
            logger.error(f"Error finding similar implementations: {e}")
            return []
    
    def enhance_skeleton_patch(
        self,
        file_path: str,
        step: messages_pb2.Step,
        target_symbol: str
    ) -> Optional[str]:
        """
        Enhance skeleton patch with RAG-retrieved examples.
        
        Args:
            file_path: Path to the file
            step: The plan step
            target_symbol: Target symbol to modify
            
        Returns:
            Enhanced skeleton patch or None
        """
        if not self.enabled:
            return None
        
        try:
            # Find similar code patterns
            step_type = self._get_step_type_string(step.kind)
            similar = self.find_similar_implementations(
                target_symbol,
                step_type,
                k=3
            )
            
            if not similar:
                return None
            
            # Build enhanced skeleton
            patch_lines = [
                f"--- a/{file_path}",
                f"+++ b/{file_path}",
                f"@@ ... @@",
                f"# Goal: {step.goal}",
                f"# Similar implementations found:",
            ]
            
            for impl in similar[:2]:
                patch_lines.extend([
                    f"#   - {impl['file']}:{impl['line']} ({impl['symbol']})",
                    f"#     Type: {impl['type']}"
                ])
            
            patch_lines.extend([
                f"",
                f"# TODO: Implement based on examples above",
                f"# Consider: {', '.join(step.hints[:2])}"
            ])
            
            return "\n".join(patch_lines)
            
        except Exception as e:
            logger.error(f"Error enhancing skeleton patch: {e}")
            return None
    
    def _create_blob_id(self, search_result: Dict[str, Any]) -> str:
        """Create a blob ID from search result."""
        # Format: file_path:start_line:end_line:chunk_hash
        file_path = search_result.get("file_path", "")
        start_line = search_result.get("start_line", 0)
        end_line = search_result.get("end_line", start_line)
        
        # Simple hash of the content
        content = search_result.get("content", "")
        chunk_hash = str(hash(content))[:8]
        
        return f"{file_path}:{start_line}:{end_line}:{chunk_hash}"
    
    def _get_snippet_for_result(self, result: Dict[str, Any]) -> str:
        """Get code snippet for a search result."""
        if not self.rag_client:
            return ""
        
        try:
            snippet = self.rag_client.get_snippet(
                file_path=result["file_path"],
                start_line=result["start_line"],
                end_line=result.get("end_line", result["start_line"]),
                context_lines=2
            )
            return snippet
        except:
            return ""
    
    def _get_step_type_string(self, step_kind: int) -> str:
        """Convert step kind enum to string."""
        step_kind_map = {
            messages_pb2.STEP_KIND_ADD: "add feature",
            messages_pb2.STEP_KIND_EDIT: "edit",
            messages_pb2.STEP_KIND_REFACTOR: "refactor",
            messages_pb2.STEP_KIND_REMOVE: "remove",
            messages_pb2.STEP_KIND_REVIEW: "review",
            messages_pb2.STEP_KIND_TEST: "test",
        }
        return step_kind_map.get(step_kind, "implementation")
    
    def index_repository(self) -> Dict[str, int]:
        """
        Index the repository if not already indexed.
        
        Returns:
            Dictionary of file -> chunk count
        """
        if not self.enabled:
            return {}
        
        try:
            # Check if already indexed
            stats = self.rag_client.get_stats()
            if stats["total_chunks"] > 0:
                logger.info(f"Repository already indexed with {stats['total_chunks']} chunks")
                return {}
            
            # Index the repository
            logger.info("Indexing repository for RAG...")
            results = self.rag_client.index_directory(
                directory=str(self.repo_path),
                extensions=[".py", ".js", ".java", ".go", ".ts", ".tsx"]
            )
            
            total_chunks = sum(results.values())
            logger.info(f"Indexed {len(results)} files, {total_chunks} chunks")
            
            return results
            
        except Exception as e:
            logger.error(f"Error indexing repository: {e}")
            return {}