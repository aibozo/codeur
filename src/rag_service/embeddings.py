"""
Embedding generation for the RAG service.
"""

import os
from typing import List, Dict, Any, Optional
import logging
from functools import lru_cache
import hashlib

from openai import OpenAI
import tiktoken

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings from text.
    
    Supports OpenAI embeddings with caching.
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding service.
        
        Args:
            model: The embedding model to use
        """
        self.model = model
        self.dimension = 1536  # Default for text-embedding-3-small
        
        # Initialize OpenAI client if available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.enabled = True
            logger.info(f"Embedding service initialized with model: {model}")
        else:
            self.client = None
            self.enabled = False
            logger.warning("OpenAI API key not found, embedding service disabled")
        
        # Token counting
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def embed_text(self, text: str, cache_key: Optional[str] = None) -> Optional[List[float]]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            cache_key: Optional cache key for the embedding
            
        Returns:
            Embedding vector or None if service is disabled
        """
        if not self.enabled:
            return None
        
        # Check cache first
        if cache_key:
            cached = self._get_cached_embedding(cache_key)
            if cached:
                return cached
        
        try:
            # Truncate text if too long
            text = self._truncate_text(text, max_tokens=8000)
            
            # Generate embedding
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            embedding = response.data[0].embedding
            
            # Cache if key provided
            if cache_key:
                self._cache_embedding(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (None for failed embeddings)
        """
        if not self.enabled:
            return [None] * len(texts)
        
        embeddings = []
        
        # Process in batches (OpenAI supports up to 2048 inputs)
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Truncate texts
            batch = [self._truncate_text(text, max_tokens=8000) for text in batch]
            
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # Add None for failed embeddings
                embeddings.extend([None] * len(batch))
        
        return embeddings
    
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to maximum token length."""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()
    
    @lru_cache(maxsize=10000)
    def _get_cached_embedding(self, cache_key: str) -> Optional[List[float]]:
        """Get cached embedding (in-memory cache for now)."""
        # TODO: Implement Redis caching
        return None
    
    def _cache_embedding(self, cache_key: str, embedding: List[float]):
        """Cache embedding (in-memory for now)."""
        # TODO: Implement Redis caching
        pass
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def estimate_cost(self, text_count: int) -> float:
        """
        Estimate cost for embedding generation.
        
        Args:
            text_count: Number of texts to embed
            
        Returns:
            Estimated cost in USD
        """
        # Pricing for text-embedding-3-small: $0.00002 per 1K tokens
        # Assume average 500 tokens per text
        avg_tokens_per_text = 500
        total_tokens = text_count * avg_tokens_per_text
        cost_per_1k_tokens = 0.00002
        
        return (total_tokens / 1000) * cost_per_1k_tokens