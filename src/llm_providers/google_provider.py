"""
Google Gemini provider implementation.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Provider for Google Gemini models."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Google provider."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not provided")
        
        self.client = genai.Client(api_key=self.api_key)
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
            logger.info(f"Google provider called with model: {model_id}")
            
            # Remove "models/" prefix if present
            if model_id.startswith("models/"):
                model_id = model_id[7:]
                logger.info(f"Removed models/ prefix, now: {model_id}")
            
            # Configure generation parameters
            generation_config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40),
                max_output_tokens=max_tokens,
                response_mime_type="text/plain",
            )
            
            # Convert messages to Gemini format
            contents = []
            
            # Handle system message
            system_instruction = None
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                    break
            
            # Convert messages to Content objects
            for msg in messages:
                if msg["role"] == "system":
                    continue  # System messages handled separately
                    
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
            
            # If there's a system instruction, prepend it to the first user message
            if system_instruction and contents:
                first_content = contents[0]
                if first_content.role == "user" and first_content.parts:
                    original_text = first_content.parts[0].text
                    first_content.parts[0] = types.Part.from_text(
                        text=f"{system_instruction}\n\n{original_text}"
                    )
            
            # Generate response using streaming (like the working example)
            content_parts = []
            
            try:
                # Use streaming to match the working example
                for chunk in self.client.models.generate_content_stream(
                    model=model_id,
                    contents=contents,
                    config=generation_config
                ):
                    if hasattr(chunk, 'text') and chunk.text:
                        content_parts.append(chunk.text)
                
                content = ''.join(content_parts)
                
            except Exception as stream_error:
                logger.warning(f"Streaming failed, trying non-streaming: {stream_error}")
                # Fallback to non-streaming
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=contents,
                    config=generation_config
                )
                
                # Extract content
                content = ""
                if hasattr(response, 'text') and response.text:
                    content = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    try:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            if candidate.content.parts:
                                content = candidate.content.parts[0].text
                    except (IndexError, AttributeError):
                        pass
            
            # Estimate token usage (Gemini doesn't always provide exact counts)
            # Using rough estimation: ~4 chars per token
            prompt_tokens = sum(len(msg["content"]) for msg in messages) // 4
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
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Model ID was: {model_id}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Re-raise the original exception
            raise
    
    def count_tokens(self, model_id: str, text: str) -> int:
        """Count tokens for a given text."""
        try:
            model = genai.GenerativeModel(model_id)
            return model.count_tokens(text).total_tokens
        except:
            # Fallback to estimation
            return len(text) // 4