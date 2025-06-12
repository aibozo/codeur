"""
Client for the RAG service.
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from .service import RAGService
from .models import SearchResult

logger = logging.getLogger(__name__)


class RAGClient:
    """
    Client interface for the RAG service.
    
    This provides a simplified interface for other components
    to interact with the RAG service.
    """
    
    def __init__(self, service: Optional[RAGService] = None):
        """
        Initialize the RAG client.
        
        Args:
            service: RAG service instance (creates default if None)
        """
        if service is None:
            # Create default service with persistence in .rag directory
            persist_dir = Path(".rag")
            persist_dir.mkdir(exist_ok=True)
            self.service = RAGService(persist_directory=str(persist_dir))
        else:
            self.service = service
    
    def search(self,
               query: str,
               k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for code.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            
        Returns:
            List of search results as dictionaries
        """
        results = self.service.search_code(query, k=k, filters=filters)
        return [result.to_dict() for result in results]
    
    def get_context(self,
                   query: str,
                   k: int = 10,
                   max_tokens: int = 3000) -> str:
        """
        Get formatted context for LLM prompts.
        
        Args:
            query: Context query
            k: Number of chunks to retrieve
            max_tokens: Maximum tokens in context
            
        Returns:
            Formatted context string
        """
        return self.service.get_context(query, k=k, max_tokens=max_tokens)
    
    def find_symbol(self,
                   symbol_name: str,
                   symbol_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find a specific symbol.
        
        Args:
            symbol_name: Name of the symbol
            symbol_type: Type of symbol (function, class, etc)
            
        Returns:
            List of search results
        """
        results = self.service.find_symbol(symbol_name, symbol_type)
        return [result.to_dict() for result in results]
    
    def get_snippet(self,
                   file_path: str,
                   start_line: int,
                   end_line: Optional[int] = None,
                   context_lines: int = 5) -> str:
        """
        Get a code snippet.
        
        Args:
            file_path: Path to the file
            start_line: Starting line
            end_line: Ending line
            context_lines: Additional context
            
        Returns:
            Code snippet
        """
        return self.service.get_snippet(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            context_lines=context_lines
        )
    
    def index_directory(self,
                       directory: str = ".",
                       extensions: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Index a directory.
        
        Args:
            directory: Directory to index
            extensions: File extensions to include
            
        Returns:
            Dictionary of file -> chunk count
        """
        return self.service.index_directory(directory, extensions=extensions)
    
    def index_file(self, file_path: str) -> int:
        """
        Index a single file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Number of chunks indexed
        """
        return self.service.index_file(file_path)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = self.service.get_stats()
        return {
            "total_chunks": stats.total_chunks,
            "total_files": stats.total_files,
            "total_embeddings": stats.total_embeddings,
            "languages": stats.languages,
            "chunk_types": stats.chunk_types
        }
    
    def is_available(self) -> bool:
        """Check if RAG service is available."""
        return self.service.embedding_service.enabled