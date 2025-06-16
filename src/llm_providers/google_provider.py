"""
Google Gemini provider implementation.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Provider for Google Gemini models."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Google provider."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not provided")
        
        genai.configure(api_key=self.api_key)
        logger.info("Google Gemini provider initialized")
    
    def create_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a completion using Gemini.
        
        Args:
            model_id: The Gemini model ID
            messages: List of message dicts with 'role' and 'content'
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Response dict with 'content' and 'usage' keys
        """
        try:
            # Initialize the model
            model = genai.GenerativeModel(model_id)
            
            # Configure generation parameters
            generation_config = {
                "temperature": temperature,
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # Configure safety settings (permissive for development)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Convert messages to Gemini format
            if len(messages) == 1:
                # Single user message
                prompt = messages[0]["content"]
            else:
                # Combine system and user messages
                parts = []
                for msg in messages:
                    if msg["role"] == "system":
                        parts.append(f"Instructions: {msg['content']}")
                    elif msg["role"] == "user":
                        parts.append(f"User: {msg['content']}")
                    elif msg["role"] == "assistant":
                        parts.append(f"Assistant: {msg['content']}")
                prompt = "\n\n".join(parts)
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Extract content
            content = response.text if response.text else ""
            
            # Estimate token usage (Gemini doesn't always provide exact counts)
            # Using rough estimation: ~4 chars per token
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(content) // 4
            
            return {
                "content": content,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Google Gemini error: {e}")
            raise
    
    def count_tokens(self, model_id: str, text: str) -> int:
        """Count tokens for a given text."""
        try:
            model = genai.GenerativeModel(model_id)
            return model.count_tokens(text).total_tokens
        except:
            # Fallback to estimation
            return len(text) // 4