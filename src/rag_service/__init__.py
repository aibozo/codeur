"""
RAG Service package.

This package provides retrieval-augmented generation capabilities
with adaptive similarity gating for improved performance.
"""

from .service import RAGService
from .client import RAGClient
from .models import CodeChunk, SearchResult, SearchRequest, IndexStats

# Import adaptive versions
from .adaptive_rag_service import AdaptiveRAGService
from .adaptive_client import AdaptiveRAGClient

# Configuration flag to use adaptive versions by default
import os
USE_ADAPTIVE_RAG = os.getenv("USE_ADAPTIVE_RAG", "true").lower() == "true"

# Override default exports if adaptive is enabled
if USE_ADAPTIVE_RAG:
    # Make adaptive versions the default
    RAGService = AdaptiveRAGService
    RAGClient = AdaptiveRAGClient
    
    # Keep originals available with explicit names
    from .service import RAGService as BaseRAGService
    from .client import RAGClient as BaseRAGClient

__all__ = [
    "RAGService",
    "RAGClient", 
    "CodeChunk",
    "SearchResult",
    "SearchRequest",
    "IndexStats",
    "AdaptiveRAGService",
    "AdaptiveRAGClient",
]

# For backward compatibility, also export base versions explicitly
if USE_ADAPTIVE_RAG:
    __all__.extend(["BaseRAGService", "BaseRAGClient"])