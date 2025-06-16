"""
Anthropic Claude provider implementation.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import anthropic

from .base import (
    LLMProvider, Message, CompletionResponse, GenerationConfig, ResponseFormat
)

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Anthropic provider."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self._supported_features = {
            "vision",
            "streaming",
            "system_messages",
            "function_calling"  # Via XML prompting
        }
        logger.info("Anthropic provider initialized")
    
    def generate(
        self,
        messages: List[Message],
        model: str,
        config: GenerationConfig = None
    ) -> CompletionResponse:
        """Generate a completion using Claude API."""
        config = config or GenerationConfig()
        
        try:
            # Separate system message from conversation
            system_message = None
            conversation = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    conversation.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Prepare API parameters
            params = {
                "model": model,
                "messages": conversation,
                "max_tokens": config.max_tokens or 4096,  # Claude requires this
                "temperature": min(config.temperature, 1.0),  # Claude max is 1.0
            }
            
            if system_message:
                params["system"] = system_message
                
            if config.stop_sequences:
                params["stop_sequences"] = config.stop_sequences
                
            # Add JSON instruction if needed
            if config.response_format == ResponseFormat.JSON:
                json_instruction = "\n\nPlease respond with valid JSON only."
                if system_message:
                    params["system"] += json_instruction
                else:
                    params["system"] = json_instruction
            
            # Make API call
            response = self.client.messages.create(**params)
            
            # Extract content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
            
            return CompletionResponse(
                content=content,
                finish_reason=response.stop_reason or "stop",
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if hasattr(response, 'usage') else None,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
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
            # Separate system message
            system_message = None
            conversation = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    conversation.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            params = {
                "model": model,
                "messages": conversation,
                "max_tokens": config.max_tokens or 4096,
                "temperature": min(config.temperature, 1.0),
                "stream": True
            }
            
            if system_message:
                params["system"] = system_message
            
            with self.client.messages.stream(**params) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for Claude model."""
        try:
            # Use Anthropic's token counting if available
            return self.client.count_tokens(text)
        except:
            # Fallback to estimation (Claude uses ~3-4 chars per token)
            return len(text) // 3
    
    def supports_feature(self, feature: str) -> bool:
        """Check if feature is supported."""
        return feature in self._supported_features
    
    def validate_model(self, model: str) -> bool:
        """Validate Claude model names."""
        valid_models = {
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        }
        # Also support future models
        return model in valid_models or model.startswith("claude-")