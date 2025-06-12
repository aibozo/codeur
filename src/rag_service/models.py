"""
Data models for the RAG service.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from enum import Enum


class ChunkType(str, Enum):
    """Types of code chunks."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    COMMENT = "comment"
    IMPORT = "import"
    GENERAL = "general"


@dataclass
class CodeChunk:
    """A chunk of code with metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    chunk_type: ChunkType = ChunkType.GENERAL
    language: str = "python"
    symbol_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def text_for_embedding(self) -> str:
        """Get the text to use for embedding generation."""
        parts = []
        
        # Add context about location
        if self.symbol_name:
            parts.append(f"{self.chunk_type.value} {self.symbol_name}")
        
        parts.append(f"File: {self.file_path}")
        
        # Add the actual content
        parts.append(self.content)
        
        return "\n".join(parts)


@dataclass
class SearchResult:
    """A search result from the RAG service."""
    chunk: CodeChunk
    score: float
    match_type: str = "hybrid"  # "vector", "keyword", or "hybrid"
    highlights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.chunk.id,
            "content": self.chunk.content,
            "file_path": self.chunk.file_path,
            "start_line": self.chunk.start_line,
            "end_line": self.chunk.end_line,
            "chunk_type": self.chunk.chunk_type,
            "symbol_name": self.chunk.symbol_name,
            "score": self.score,
            "match_type": self.match_type,
            "highlights": self.highlights
        }


@dataclass
class SearchRequest:
    """A search request to the RAG service."""
    query: str
    k: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)
    alpha: float = 0.5  # Weight for hybrid search (0=keyword only, 1=vector only)
    include_code: bool = True
    include_docs: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "k": self.k,
            "filters": self.filters,
            "alpha": self.alpha,
            "include_code": self.include_code,
            "include_docs": self.include_docs
        }


@dataclass
class IndexStats:
    """Statistics about the RAG index."""
    total_chunks: int = 0
    total_files: int = 0
    total_embeddings: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    chunk_types: Dict[str, int] = field(default_factory=dict)
    last_updated: Optional[datetime] = None