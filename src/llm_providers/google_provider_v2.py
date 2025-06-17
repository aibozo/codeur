"""
Google Gemini provider implementation following unified interface.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import (
    LLMProvider, Message, CompletionResponse, GenerationConfig, ResponseFormat
)

logger = logging.getLogger(__name__)


class GoogleProviderV2(LLMProvider):
    """Provider for Google Gemini models."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Google provider."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not provided")
        
        genai.configure(api_key=self.api_key)
        self._supported_features = {
            "vision",
            "streaming",
            "system_messages",
            "json_mode"  # Through prompting
        }
        logger.info("Google Gemini provider initialized")
    
    def generate(
        self,
        messages: List[Message],
        model: str,
        config: GenerationConfig = None
    ) -> CompletionResponse:
        """Generate a completion using Gemini API."""
        config = config or GenerationConfig()
        
        try:
            # Initialize the model
            gemini_model = genai.GenerativeModel(model)
            
            # Configure generation parameters
            generation_config = {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k or 40,
            }
            
            if config.max_tokens:
                generation_config["max_output_tokens"] = config.max_tokens
                
            if config.stop_sequences:
                generation_config["stop_sequences"] = config.stop_sequences
            
            # Configure safety settings (permissive for development)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Convert messages to Gemini format
            prompt = self._format_messages(messages, config.response_format)
            logger.debug(f"Using Gemini model: {model}")
            logger.debug(f"Sending prompt to Gemini (first 500 chars): {prompt[:500]}")
            logger.debug(f"Total prompt length: {len(prompt)} chars")
            logger.debug(f"Generation config: temperature={generation_config.get('temperature')}, max_output_tokens={generation_config.get('max_output_tokens')}")
            
            # Generate response
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Debug response
            logger.debug(f"Gemini response candidates: {len(response.candidates) if response.candidates else 0}")
            if response.candidates:
                candidate = response.candidates[0]
                logger.debug(f"Finish reason: {candidate.finish_reason}")
                logger.debug(f"Safety ratings: {candidate.safety_ratings}")
                if candidate.content and candidate.content.parts:
                    logger.debug(f"Parts count: {len(candidate.content.parts)}")
                else:
                    logger.debug("No content parts in response")
            
            # Extract content with better error handling
            content = ""
            try:
                content = response.text
            except ValueError as e:
                # Log detailed information about the response
                logger.warning(f"Failed to get text from response: {e}")
                if response.candidates:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        # Try to extract text from parts manually
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                text_parts.append(part.text)
                        content = "".join(text_parts)
                        logger.info(f"Manually extracted {len(content)} chars from parts")
                    else:
                        logger.warning("No content parts available")
                        # Check if it's a refusal or empty response
                        if candidate.finish_reason == 2:  # STOP
                            logger.warning("Model returned STOP with no content - possibly prompt issue")
                        elif candidate.finish_reason == 3:  # MAX_TOKENS
                            logger.warning("Model hit max tokens limit")
                        elif candidate.finish_reason == 4:  # SAFETY
                            logger.warning("Content blocked by safety filters")
                            logger.warning(f"Safety ratings: {candidate.safety_ratings}")
                else:
                    logger.error("No candidates in response")
            
            # Estimate token usage (Gemini doesn't always provide exact counts)
            prompt_tokens = self.count_tokens(prompt, model)
            completion_tokens = self.count_tokens(content, model)
            
            return CompletionResponse(
                content=content,
                finish_reason="stop",
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                },
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Google Gemini error: {e}")
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
            gemini_model = genai.GenerativeModel(model)
            
            generation_config = {
                "temperature": config.temperature,
                "top_p": config.top_p,
            }
            
            if config.max_tokens:
                generation_config["max_output_tokens"] = config.max_tokens
            
            prompt = self._format_messages(messages, config.response_format)
            
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Google Gemini streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for Gemini model."""
        try:
            gemini_model = genai.GenerativeModel(model)
            return gemini_model.count_tokens(text).total_tokens
        except:
            # Fallback to estimation
            return len(text) // 4
    
    def supports_feature(self, feature: str) -> bool:
        """Check if feature is supported."""
        return feature in self._supported_features
    
    def validate_model(self, model: str) -> bool:
        """Validate Gemini model names."""
        valid_models = {
            "gemini-pro", "gemini-pro-vision",
            "gemini-1.5-pro", "gemini-1.5-flash",
            "gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"
        }
        return model in valid_models or model.startswith("gemini-")
    
    def _format_messages(self, messages: List[Message], response_format: ResponseFormat) -> str:
        """Format messages for Gemini."""
        # Gemini works best with simple concatenated prompts
        # System messages can be prepended as context
        
        prompt_parts = []
        
        # First, add any system messages as context
        system_messages = [msg for msg in messages if msg.role == "system"]
        if system_messages:
            system_content = "\n".join(msg.content for msg in system_messages)
            prompt_parts.append(system_content)
        
        # Then add the conversation
        for msg in messages:
            if msg.role == "user":
                prompt_parts.append(msg.content)
            elif msg.role == "assistant":
                # For multi-turn conversations, include assistant responses
                prompt_parts.append(msg.content)
        
        prompt = "\n\n".join(prompt_parts)
        
        # Add JSON instruction if needed
        if response_format == ResponseFormat.JSON:
            prompt += "\n\nRespond with valid JSON format only."
        
        return prompt