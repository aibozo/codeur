"""
Base interface for LLM providers.

This module defines the common interface that all LLM providers must implement,
ensuring consistent behavior across OpenAI, Google, and Anthropic providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ResponseFormat(Enum):
    """Supported response formats."""
    TEXT = "text"
    JSON = "json_object"
    

@dataclass
class GenerationConfig:
    """Common generation configuration."""
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 0.95
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    response_format: ResponseFormat = ResponseFormat.TEXT
    

@dataclass
class Message:
    """Standard message format."""
    role: str  # system, user, assistant
    content: str
    

@dataclass
class CompletionResponse:
    """Standard completion response."""
    content: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = None  # prompt_tokens, completion_tokens, total_tokens
    raw_response: Any = None  # Original provider response for debugging
    

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement these methods to ensure compatibility
    with the unified LLM client system.
    """
    
    @abstractmethod
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the provider with API key."""
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: List[Message],
        model: str,
        config: GenerationConfig = None
    ) -> CompletionResponse:
        """
        Generate a completion from messages.
        
        Args:
            messages: List of conversation messages
            model: Model identifier
            config: Generation configuration
            
        Returns:
            CompletionResponse with generated text and metadata
        """
        pass
    
    @abstractmethod
    def generate_stream(
        self,
        messages: List[Message],
        model: str,
        config: GenerationConfig = None
    ):
        """
        Generate a streaming completion.
        
        Yields partial responses as they arrive.
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in text for a specific model.
        
        Args:
            text: Text to count tokens for
            model: Model to use for tokenization
            
        Returns:
            Number of tokens
        """
        pass
    
    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """
        Check if provider supports a specific feature.
        
        Features might include:
        - function_calling
        - json_mode
        - vision
        - streaming
        - system_messages
        
        Args:
            feature: Feature name to check
            
        Returns:
            True if feature is supported
        """
        pass
    
    def validate_model(self, model: str) -> bool:
        """
        Validate if model is supported by this provider.
        
        Override in subclasses for provider-specific validation.
        """
        return True
    
    def prepare_messages(self, messages: List[Message]) -> Any:
        """
        Convert messages to provider-specific format.
        
        Override in subclasses if needed.
        """
        return [{"role": m.role, "content": m.content} for m in messages]