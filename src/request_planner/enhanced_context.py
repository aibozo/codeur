"""
Enhanced context retrieval using the RAG service.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..rag_service import RAGClient, RAGService
from .models import SearchResult as SimpleSearchResult

logger = logging.getLogger(__name__)


class EnhancedContextRetriever:
    """
    Enhanced context retriever that uses the RAG service.
    
    Falls back to simple search if RAG is not available.
    """
    
    def __init__(self, repo_path: Path, use_rag: bool = True):
        """
        Initialize the enhanced context retriever.
        
        Args:
            repo_path: Path to the repository
            use_rag: Whether to use RAG service
        """
        self.repo_path = repo_path
        self.use_rag = use_rag
        
        # Try to initialize RAG client
        if use_rag:
            try:
                # Create RAG service with repo-specific persistence
                rag_dir = repo_path / ".rag"
                rag_service = RAGService(persist_directory=str(rag_dir))
                self.rag_client = RAGClient(service=rag_service)
                
                # Check if index exists, if not, index the repo
                stats = self.rag_client.get_stats()
                if stats["total_chunks"] == 0:
                    logger.info("No RAG index found, indexing repository...")
                    self._index_repository()
                
                self.rag_available = self.rag_client.is_available()
                if self.rag_available:
                    logger.info("RAG service initialized successfully")
                else:
                    logger.warning("RAG service initialized but embeddings not available")
                    
            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {e}")
                self.rag_client = None
                self.rag_available = False
        else:
            self.rag_client = None
            self.rag_available = False
        
        # Initialize simple context retriever as fallback
        from .context import ContextRetriever
        self.simple_retriever = ContextRetriever(repo_path)
    
    def get_context(self, query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get relevant context for a query and intent.
        
        Args:
            query: The user's query
            intent: Parsed intent information
            
        Returns:
            Context information including relevant files and snippets
        """
        if self.rag_available:
            return self._get_rag_context(query, intent)
        else:
            return self.simple_retriever.get_context(query, intent)
    
    def search(self, query: str, limit: int = 10) -> List[SimpleSearchResult]:
        """
        Search the codebase.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        if self.rag_available:
            # Use RAG search
            rag_results = self.rag_client.search(query, k=limit)
            
            # Convert to simple search results
            simple_results = []
            for result in rag_results:
                simple_result = SimpleSearchResult(
                    file=result["file_path"],
                    line=result["start_line"],
                    content=result["content"],
                    score=result["score"]
                )
                simple_results.append(simple_result)
            
            return simple_results
        else:
            # Use simple search
            return self.simple_retriever.search(query, limit=limit)
    
    def _get_rag_context(self, query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Get context using RAG service."""
        context = {
            "query": query,
            "intent": intent,
            "relevant_files": [],
            "snippets": [],
            "using_rag": True
        }
        
        # Search for relevant code
        search_results = self.rag_client.search(query, k=20)
        
        # Extract relevant files and snippets
        seen_files = set()
        for result in search_results:
            file_path = result["file_path"]
            
            # Track unique files
            if file_path not in seen_files:
                seen_files.add(file_path)
                context["relevant_files"].append(file_path)
            
            # Add snippet
            snippet = {
                "file": file_path,
                "line": result["start_line"],
                "content": result["content"],
                "type": result.get("chunk_type", "general"),
                "symbol": result.get("symbol_name"),
                "score": result["score"]
            }
            context["snippets"].append(snippet)
        
        # Add intent-specific searches
        if intent["type"] == "add_feature" and "target" in intent:
            # Look for similar features
            similar_results = self.rag_client.find_symbol(intent["target"])
            context["similar_features"] = [
                {
                    "file": r["file_path"],
                    "name": r.get("symbol_name", "unknown"),
                    "type": r.get("chunk_type", "unknown"),
                    "similarity": r["score"]
                }
                for r in similar_results[:5]
            ]
        
        # Get formatted context for LLM
        context["formatted_context"] = self.rag_client.get_context(
            query=query,
            k=10,
            max_tokens=3000
        )
        
        return context
    
    def _index_repository(self):
        """Index the repository for RAG search."""
        try:
            logger.info(f"Indexing repository: {self.repo_path}")
            
            # Index Python files for now
            results = self.rag_client.index_directory(
                directory=str(self.repo_path),
                extensions=[".py"]  # Start with Python only
            )
            
            total_chunks = sum(results.values())
            logger.info(f"Indexed {len(results)} files, {total_chunks} chunks")
            
        except Exception as e:
            logger.error(f"Failed to index repository: {e}")
    
    def update_index(self, file_path: str):
        """Update index for a specific file."""
        if self.rag_available:
            try:
                chunks = self.rag_client.index_file(file_path)
                logger.info(f"Updated index for {file_path}: {chunks} chunks")
            except Exception as e:
                logger.error(f"Failed to update index for {file_path}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG index statistics."""
        if self.rag_available:
            return self.rag_client.get_stats()
        else:
            return {
                "rag_available": False,
                "message": "RAG service not available"
            }