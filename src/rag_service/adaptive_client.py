"""
Adaptive RAG Client with integrated similarity gating.

This provides a drop-in replacement for RAGClient with adaptive features.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from .client import RAGClient
from .adaptive_rag_service import AdaptiveRAGService
from .models import SearchResult

logger = logging.getLogger(__name__)


class AdaptiveRAGClient(RAGClient):
    """
    Enhanced RAG client with adaptive similarity gating.
    
    This is a drop-in replacement for RAGClient that adds:
    - Adaptive similarity filtering
    - Quality feedback integration
    - Project-specific learning
    """
    
    def __init__(self,
                 service: Optional[AdaptiveRAGService] = None,
                 enable_adaptive_gating: bool = True):
        """
        Initialize the adaptive RAG client.
        
        Args:
            service: Adaptive RAG service instance
            enable_adaptive_gating: Whether to enable adaptive features
        """
        # If service is a regular RAGService, upgrade it
        if service and not isinstance(service, AdaptiveRAGService):
            service = AdaptiveRAGService.from_existing_service(
                service,
                enable_adaptive_gating=enable_adaptive_gating
            )
        
        super().__init__(service=service)
        self.adaptive_service = service
        self._current_project_id = None
    
    def set_project_context(self, project_id: str):
        """
        Set the current project context for adaptive thresholds.
        
        Args:
            project_id: Project identifier
        """
        self._current_project_id = project_id
        logger.debug(f"Set project context: {project_id}")
    
    def search(self,
              query: str,
              k: int = 10,
              filters: Optional[Dict[str, Any]] = None,
              retrieval_type: str = "code_search") -> List[SearchResult]:
        """
        Enhanced search with adaptive filtering.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            retrieval_type: Type of retrieval
            
        Returns:
            List of adaptively filtered results
        """
        if not self.adaptive_service:
            return super().search(query, k, filters)
        
        return self.adaptive_service.search_code(
            query=query,
            k=k,
            filters=filters,
            project_id=self._current_project_id,
            retrieval_type=retrieval_type
        )
    
    def get_context(self,
                   query: str,
                   k: int = 10,
                   max_tokens: int = 3000,
                   auto_critique: bool = True):
        """
        Get context with optional quality analysis.
        
        Args:
            query: Context query
            k: Number of chunks
            max_tokens: Maximum tokens
            auto_critique: Whether to run quality critique
            
        Returns:
            If auto_critique is True and adaptive service is available:
                Tuple of (formatted context, critique summary)
            Otherwise:
                Just the formatted context string (for compatibility)
        """
        if not self.adaptive_service or not self.adaptive_service.enable_adaptive_gating:
            # Return just context for compatibility
            return super().get_context(query, k, max_tokens)
        
        # Get enhanced context with optional critique
        context, critique = self.adaptive_service.get_context(
            query=query,
            k=k,
            max_tokens=max_tokens,
            project_id=self._current_project_id,
            auto_critique=auto_critique
        )
        
        # Return based on whether critique was requested
        if auto_critique and critique:
            return context, critique
        else:
            return context  # Maintain compatibility when critique not requested
    
    def get_adaptive_stats(self) -> Dict[str, Any]:
        """
        Get adaptive gating statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.adaptive_service:
            return {"enabled": False}
        
        return self.adaptive_service.get_adaptive_stats(
            project_id=self._current_project_id
        )
    
    def reset_adaptive_profile(self):
        """Reset adaptive profile for current project."""
        if self.adaptive_service:
            self.adaptive_service.reset_adaptive_profile(
                project_id=self._current_project_id
            )
    
    def provide_feedback(self,
                        chunk_ids: List[str],
                        useful: List[bool],
                        missing_context: Optional[str] = None,
                        unnecessary_chunks: Optional[List[str]] = None):
        """
        Provide explicit feedback for adaptive learning.
        
        Args:
            chunk_ids: IDs of retrieved chunks
            useful: Whether each chunk was useful
            missing_context: Description of missing information
            unnecessary_chunks: IDs of unnecessary chunks
        """
        if not self.adaptive_service or not self.adaptive_service.enable_adaptive_gating:
            return
        
        feedback = {
            "chunk_ids": chunk_ids,
            "useful": useful,
            "missing_context": missing_context,
            "unnecessary_chunks": unnecessary_chunks or []
        }
        
        self.adaptive_service.similarity_gate.record_feedback(
            project_id=self._current_project_id or "default",
            retrieval_type="manual_feedback",
            feedback=feedback
        )
    
    # Maintain compatibility with base client methods
    def find_symbol(self, symbol_name: str, symbol_type: Optional[str] = None) -> List[SearchResult]:
        """Find symbol with adaptive filtering."""
        results = super().find_symbol(symbol_name, symbol_type)
        
        # Apply post-filtering if adaptive service available
        if self.adaptive_service and self.adaptive_service.enable_adaptive_gating:
            # Could apply additional filtering here if needed
            pass
        
        return results
    
    def find_similar_code(self,
                         code_snippet: str,
                         k: int = 10,
                         language: Optional[str] = None) -> List[SearchResult]:
        """Find similar code with adaptive filtering."""
        # Create a temporary chunk for similarity search
        from .models import CodeChunk
        import uuid
        
        temp_chunk = CodeChunk(
            id=str(uuid.uuid4()),
            content=code_snippet,
            file_path="<snippet>",
            start_line=1,
            end_line=len(code_snippet.split('\n')),
            chunk_type="general",
            language=language or "python"
        )
        
        if self.adaptive_service:
            return self.adaptive_service.find_similar(
                chunk=temp_chunk,
                k=k,
                project_id=self._current_project_id
            )
        
        return self.service.find_similar(temp_chunk, k)
    
    @classmethod
    def from_rag_client(cls,
                       client: RAGClient,
                       enable_adaptive_gating: bool = True) -> 'AdaptiveRAGClient':
        """
        Create adaptive client from existing RAG client.
        
        Args:
            client: Existing RAG client
            enable_adaptive_gating: Whether to enable adaptive features
            
        Returns:
            New adaptive RAG client
        """
        # Create adaptive service from the client's service
        adaptive_service = AdaptiveRAGService.from_existing_service(
            client.service,
            enable_adaptive_gating=enable_adaptive_gating
        )
        
        return cls(service=adaptive_service)