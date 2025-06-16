"""
OpenAI provider implementation.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
import tiktoken

from .base import (
    LLMProvider, Message, CompletionResponse, GenerationConfig, ResponseFormat
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models including GPT-4, o1, and o3 series."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not provided")
        
        self.client = OpenAI(api_key=self.api_key)
        self._supported_features = {
            "function_calling",
            "json_mode",
            "vision",
            "streaming",
            "system_messages"
        }
        logger.info("OpenAI provider initialized")
    
    def generate(
        self,
        messages: List[Message],
        model: str,
        config: GenerationConfig = None
    ) -> CompletionResponse:
        """Generate a completion using OpenAI API."""
        config = config or GenerationConfig()
        
        try:
            # Prepare API parameters
            params = {
                "model": model,
                "messages": self.prepare_messages(messages),
                "temperature": config.temperature,
                "top_p": config.top_p,
            }
            
            # Handle model-specific parameters
            if model.startswith("o3"):
                # o3 models have specific requirements
                params["response_format"] = {"type": "text"}
                params["reasoning_effort"] = "medium" if model == "o3" else "low"
                # o3 doesn't support temperature
                params.pop("temperature")
            else:
                # Standard models
                if config.max_tokens:
                    params["max_tokens"] = config.max_tokens
                    
                if config.response_format == ResponseFormat.JSON:
                    params["response_format"] = {"type": "json_object"}
                    
                if config.stop_sequences:
                    params["stop"] = config.stop_sequences
            
            # Make API call
            response = self.client.chat.completions.create(**params)
            
            # Extract response
            message = response.choices[0].message
            content = message.content
            
            # Handle function calls if present
            if hasattr(message, 'function_call') and message.function_call:
                content = message.function_call.arguments
            
            return CompletionResponse(
                content=content,
                finish_reason=response.choices[0].finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def generate_stream(
        self,
        messages: List[Message],
        model: str,
        config: GenerationConfig = None
    ):
        """Generate streaming completion."""
        config = config or GenerationConfig()
        
        try:
            params = {
                "model": model,
                "messages": self.prepare_messages(messages),
                "temperature": config.temperature,
                "stream": True
            }
            
            if config.max_tokens:
                params["max_tokens"] = config.max_tokens
            
            stream = self.client.chat.completions.create(**params)
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens using tiktoken."""
        try:
            # Use tiktoken for accurate token counting
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback for unknown models
            return len(text) // 4
    
    def supports_feature(self, feature: str) -> bool:
        """Check if feature is supported."""
        return feature in self._supported_features
    
    def validate_model(self, model: str) -> bool:
        """Validate OpenAI model names."""
        valid_prefixes = (
            "gpt-3.5", "gpt-4", "o1", "o3", "text-embedding",
            "dall-e", "whisper", "tts"
        )
        return any(model.startswith(prefix) for prefix in valid_prefixes)