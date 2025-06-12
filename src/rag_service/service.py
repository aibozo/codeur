"""
Main RAG service implementation.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import asyncio
from concurrent.futures import ProcessPoolExecutor
import time

from .models import CodeChunk, SearchResult, SearchRequest, IndexStats
from .embeddings import EmbeddingService
from .vector_store import VectorStore
from .chunker import CodeChunker
from .search import CodeSearch

logger = logging.getLogger(__name__)


class RAGService:
    """
    Main RAG service for code search and retrieval.
    
    Provides:
    - Code indexing with embeddings
    - Hybrid search (vector + keyword)
    - Incremental updates
    - Multi-language support
    """
    
    def __init__(self,
                 persist_directory: Optional[str] = None,
                 embedding_model: str = "text-embedding-3-small",
                 chunk_size: int = 1500,
                 chunk_overlap: int = 200):
        """
        Initialize the RAG service.
        
        Args:
            persist_directory: Directory for persistence
            embedding_model: OpenAI embedding model to use
            chunk_size: Size of code chunks
            chunk_overlap: Overlap between chunks
        """
        # Set up persistence directory
        if persist_directory:
            self.persist_dir = Path(persist_directory)
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            vector_store_dir = str(self.persist_dir / "vector_store")
        else:
            self.persist_dir = None
            vector_store_dir = None
        
        # Initialize components
        self.embedding_service = EmbeddingService(model=embedding_model)
        self.vector_store = VectorStore(
            persist_directory=vector_store_dir,
            collection_name="code_chunks"
        )
        self.chunker = CodeChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.search = CodeSearch(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service
        )
        
        # Track indexed files
        self.indexed_files = set()
        self._load_indexed_files()
        
        logger.info("RAG service initialized")
    
    def index_file(self, file_path: str, content: Optional[str] = None) -> int:
        """
        Index a single file.
        
        Args:
            file_path: Path to the file
            content: File content (read from disk if None)
            
        Returns:
            Number of chunks indexed
        """
        try:
            # Read content if not provided
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Delete existing chunks for this file
            self.vector_store.delete_by_file(file_path)
            
            # Chunk the file
            chunks = self.chunker.chunk_file(
                content=content,
                file_path=file_path
            )
            
            if not chunks:
                logger.warning(f"No chunks created for {file_path}")
                return 0
            
            # Generate embeddings if service is available
            if self.embedding_service.enabled:
                # Prepare texts for embedding
                texts = [chunk.text_for_embedding for chunk in chunks]
                
                # Generate embeddings in batch
                embeddings = self.embedding_service.embed_batch(texts)
                
                # Assign embeddings to chunks
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
            
            # Add to vector store
            added = self.vector_store.add_chunks(chunks)
            
            # Track indexed file
            self.indexed_files.add(file_path)
            self._save_indexed_files()
            
            logger.info(f"Indexed {added} chunks from {file_path}")
            return added
            
        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}")
            return 0
    
    def index_directory(self, 
                       directory: str,
                       extensions: Optional[List[str]] = None,
                       exclude_patterns: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Index all files in a directory.
        
        Args:
            directory: Directory to index
            extensions: File extensions to include
            exclude_patterns: Patterns to exclude
            
        Returns:
            Dictionary of file_path -> chunk_count
        """
        directory = Path(directory)
        
        # Default extensions
        if extensions is None:
            extensions = [
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
                '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php', '.swift'
            ]
        
        # Default exclude patterns
        if exclude_patterns is None:
            exclude_patterns = [
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'build', 'dist', '.pytest_cache', '.mypy_cache'
            ]
        
        # Find files to index
        files_to_index = []
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                # Check exclude patterns
                skip = False
                for pattern in exclude_patterns:
                    if pattern in str(file_path):
                        skip = True
                        break
                
                if not skip and file_path.is_file():
                    files_to_index.append(str(file_path))
        
        # Index files
        results = {}
        total_chunks = 0
        
        logger.info(f"Indexing {len(files_to_index)} files from {directory}")
        
        for i, file_path in enumerate(files_to_index):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(files_to_index)} files")
            
            chunks = self.index_file(file_path)
            results[file_path] = chunks
            total_chunks += chunks
        
        logger.info(f"Indexed {total_chunks} chunks from {len(files_to_index)} files")
        return results
    
    def search_code(self,
                   query: str,
                   k: int = 10,
                   filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for code.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            
        Returns:
            List of search results
        """
        return self.search.search(
            query=query,
            k=k,
            filters=filters,
            search_type="hybrid"
        )
    
    def get_context(self,
                   query: str,
                   k: int = 10,
                   max_tokens: int = 3000) -> str:
        """
        Get context for LLM prompts.
        
        Args:
            query: Context query
            k: Number of chunks to retrieve
            max_tokens: Maximum tokens in context
            
        Returns:
            Formatted context string
        """
        # Search for relevant chunks
        results = self.search_code(query, k=k)
        
        if not results:
            return "No relevant context found."
        
        # Format context
        context_parts = []
        total_tokens = 0
        
        for result in results:
            chunk = result.chunk
            
            # Format chunk
            chunk_text = f"""File: {chunk.file_path}:{chunk.start_line}-{chunk.end_line}
```{chunk.language}
{chunk.content}
```
"""
            
            # Check token count
            chunk_tokens = self.embedding_service.count_tokens(chunk_text)
            if total_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            total_tokens += chunk_tokens
        
        return "\n".join(context_parts)
    
    def find_symbol(self,
                   symbol_name: str,
                   symbol_type: Optional[str] = None) -> List[SearchResult]:
        """
        Find a specific symbol.
        
        Args:
            symbol_name: Name of the symbol
            symbol_type: Type of symbol (function, class, etc)
            
        Returns:
            List of search results
        """
        filters = {}
        if symbol_type:
            filters["chunk_type"] = symbol_type
        
        return self.search.search_by_symbol(
            symbol_name=symbol_name,
            filters=filters
        )
    
    def get_snippet(self,
                   file_path: str,
                   start_line: int,
                   end_line: Optional[int] = None,
                   context_lines: int = 5) -> str:
        """
        Get a code snippet from a file.
        
        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number (None for single line)
            context_lines: Additional context lines
            
        Returns:
            Code snippet
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Adjust indices (1-based to 0-based)
            start_idx = max(0, start_line - 1 - context_lines)
            end_idx = min(len(lines), (end_line or start_line) + context_lines)
            
            # Extract snippet
            snippet_lines = lines[start_idx:end_idx]
            
            # Add line numbers
            formatted_lines = []
            for i, line in enumerate(snippet_lines):
                line_no = start_idx + i + 1
                formatted_lines.append(f"{line_no:4d} | {line.rstrip()}")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Error getting snippet: {e}")
            return f"Error reading file: {file_path}"
    
    def get_stats(self) -> IndexStats:
        """Get statistics about the index."""
        vector_stats = self.vector_store.get_stats()
        
        return IndexStats(
            total_chunks=vector_stats.get("total_chunks", 0),
            total_files=len(self.indexed_files),
            total_embeddings=vector_stats.get("total_chunks", 0),
            languages=vector_stats.get("languages", {}),
            chunk_types=vector_stats.get("chunk_types", {})
        )
    
    def clear_index(self):
        """Clear the entire index."""
        # TODO: Implement proper index clearing
        logger.warning("Index clearing not fully implemented")
        self.indexed_files.clear()
        self._save_indexed_files()
    
    def _load_indexed_files(self):
        """Load list of indexed files."""
        if self.persist_dir:
            index_file = self.persist_dir / "indexed_files.txt"
            if index_file.exists():
                with open(index_file, 'r') as f:
                    self.indexed_files = set(line.strip() for line in f)
    
    def _save_indexed_files(self):
        """Save list of indexed files."""
        if self.persist_dir:
            index_file = self.persist_dir / "indexed_files.txt"
            with open(index_file, 'w') as f:
                for file_path in sorted(self.indexed_files):
                    f.write(f"{file_path}\n")