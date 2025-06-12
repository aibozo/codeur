"""
Vector store implementation for the RAG service.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from datetime import datetime
import re

import chromadb
from chromadb.config import Settings
import numpy as np

from .models import CodeChunk, SearchResult

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector store for code embeddings using ChromaDB.
    
    This is the MVP implementation. Will be replaced with Qdrant
    for production use.
    """
    
    def __init__(self, 
                 persist_directory: Optional[str] = None,
                 collection_name: str = "code_chunks"):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory for persistence (None for in-memory)
            collection_name: Name of the collection
        """
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        if persist_directory:
            self.persist_directory = Path(persist_directory)
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        else:
            self.client = chromadb.EphemeralClient(
                settings=Settings(anonymized_telemetry=False)
            )
        
        # Get or create collection
        # We need to specify that we'll handle embeddings ourselves
        # to prevent ChromaDB from using its default embedding function
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            # Create collection without embedding function since we provide our own
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=None  # Disable default embedding function
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def add_chunks(self, chunks: List[CodeChunk]) -> int:
        """
        Add code chunks to the vector store.
        
        Args:
            chunks: List of code chunks with embeddings
            
        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0
        
        # Filter chunks with embeddings
        chunks_with_embeddings = [c for c in chunks if c.embedding is not None]
        
        if not chunks_with_embeddings:
            logger.warning("No chunks with embeddings to add")
            return 0
        
        # Prepare data for ChromaDB
        ids = [chunk.id for chunk in chunks_with_embeddings]
        embeddings = [chunk.embedding for chunk in chunks_with_embeddings]
        
        # Prepare metadata
        metadatas = []
        for chunk in chunks_with_embeddings:
            metadata = {
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "language": chunk.language,
                "created_at": chunk.created_at.isoformat()
            }
            
            if chunk.symbol_name:
                metadata["symbol_name"] = chunk.symbol_name
            
            # Add custom metadata
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
            
            metadatas.append(metadata)
        
        # Prepare documents (for keyword search)
        documents = [chunk.content for chunk in chunks_with_embeddings]
        
        # Add to collection
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
            logger.info(f"Added {len(chunks_with_embeddings)} chunks to vector store")
            return len(chunks_with_embeddings)
            
        except Exception as e:
            logger.error(f"Error adding chunks to vector store: {e}")
            return 0
    
    def search(self, 
               query_embedding: List[float],
               k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[Tuple[CodeChunk, float]]:
        """
        Search for similar code chunks.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of (chunk, score) tuples
        """
        try:
            # Build where clause from filters
            where = {}
            if filters:
                for key, value in filters.items():
                    if key in ["file_path", "language", "chunk_type"]:
                        where[key] = value
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where if where else None
            )
            
            # Parse results
            chunks_with_scores = []
            
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # Reconstruct chunk
                    chunk_id = results['ids'][0][i]
                    metadata = results['metadatas'][0][i]
                    document = results['documents'][0][i]
                    distance = results['distances'][0][i]
                    
                    # Convert distance to similarity score (1 - cosine distance)
                    score = 1.0 - distance
                    
                    # Create chunk object
                    chunk = CodeChunk(
                        id=chunk_id,
                        content=document,
                        file_path=metadata.get('file_path', ''),
                        start_line=metadata.get('start_line', 0),
                        end_line=metadata.get('end_line', 0),
                        chunk_type=metadata.get('chunk_type', 'general'),
                        language=metadata.get('language', 'unknown'),
                        symbol_name=metadata.get('symbol_name'),
                        metadata={k: v for k, v in metadata.items() 
                                if k not in ['file_path', 'start_line', 'end_line', 
                                           'chunk_type', 'language', 'symbol_name']}
                    )
                    
                    chunks_with_scores.append((chunk, score))
            
            return chunks_with_scores
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def keyword_search(self,
                      query: str,
                      k: int = 10,
                      filters: Optional[Dict[str, Any]] = None) -> List[Tuple[CodeChunk, float]]:
        """
        Keyword search implementation.
        
        Note: We implement our own keyword search instead of using ChromaDB's
        query_texts to avoid embedding dimension mismatches. ChromaDB's default
        embedding function creates 384D embeddings while we use 1536D embeddings
        from OpenAI's text-embedding-3-small model.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of (chunk, score) tuples
        """
        try:
            # Build where clause
            where = {}
            if filters:
                for key, value in filters.items():
                    if key in ["file_path", "language", "chunk_type"]:
                        where[key] = value
            
            # Use ChromaDB's document search instead of query_texts
            # This searches the stored documents without creating new embeddings
            all_results = self.collection.get(
                where=where if where else None,
                include=["documents", "metadatas"]
            )
            
            # Perform keyword matching on documents
            chunks_with_scores = []
            
            if all_results['ids']:
                # Convert query to lowercase for case-insensitive search
                query_lower = query.lower()
                query_words = query_lower.split()
                
                # Score each document based on keyword matches
                scored_chunks = []
                
                for i in range(len(all_results['ids'])):
                    chunk_id = all_results['ids'][i]
                    metadata = all_results['metadatas'][i]
                    document = all_results['documents'][i]
                    
                    # Calculate keyword match score
                    document_lower = document.lower()
                    score = 0.0
                    
                    # Count exact word matches
                    for word in query_words:
                        if len(word) >= 2:  # Skip very short words
                            count = document_lower.count(word)
                            if count > 0:
                                # Give higher score for more occurrences, with diminishing returns
                                score += min(count * 0.1, 0.5)
                    
                    # Bonus for exact phrase match
                    if query_lower in document_lower:
                        score += 0.5
                    
                    # Normalize score to 0-1 range
                    score = min(score / max(len(query_words), 1), 1.0)
                    
                    if score > 0:
                        chunk = CodeChunk(
                            id=chunk_id,
                            content=document,
                            file_path=metadata.get('file_path', ''),
                            start_line=metadata.get('start_line', 0),
                            end_line=metadata.get('end_line', 0),
                            chunk_type=metadata.get('chunk_type', 'general'),
                            language=metadata.get('language', 'unknown'),
                            symbol_name=metadata.get('symbol_name'),
                            metadata={k: v for k, v in metadata.items() 
                                    if k not in ['file_path', 'start_line', 'end_line', 
                                               'chunk_type', 'language', 'symbol_name']}
                        )
                        scored_chunks.append((chunk, score))
                
                # Sort by score and return top k
                scored_chunks.sort(key=lambda x: x[1], reverse=True)
                chunks_with_scores = scored_chunks[:k]
            
            return chunks_with_scores
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def delete_by_file(self, file_path: str) -> int:
        """
        Delete all chunks for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Number of chunks deleted
        """
        try:
            # Get all chunks for the file
            results = self.collection.get(
                where={"file_path": file_path}
            )
            
            if results['ids']:
                # Delete chunks
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for {file_path}")
                return len(results['ids'])
            
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        try:
            # Get collection info
            count = self.collection.count()
            
            # Get sample to analyze
            sample = self.collection.get(limit=1000)
            
            # Analyze metadata
            languages = {}
            chunk_types = {}
            file_count = set()
            
            if sample['metadatas']:
                for metadata in sample['metadatas']:
                    # Count languages
                    lang = metadata.get('language', 'unknown')
                    languages[lang] = languages.get(lang, 0) + 1
                    
                    # Count chunk types
                    chunk_type = metadata.get('chunk_type', 'general')
                    chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                    
                    # Count unique files
                    file_path = metadata.get('file_path')
                    if file_path:
                        file_count.add(file_path)
            
            return {
                "total_chunks": count,
                "total_files": len(file_count),
                "languages": languages,
                "chunk_types": chunk_types,
                "collection_name": self.collection_name
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}