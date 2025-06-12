"""
Shared LLM client for all agents.

Provides a simple interface for generating text with OpenAI models.
"""

import os
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Generic LLM client for text generation.
    
    Can be used by any agent for generating code, text, or other content.
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            model: Model to use (defaults to GENERAL_MODEL env var or gpt-4o)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set.\n"
                "Please either:\n"
                "1. Export it: export OPENAI_API_KEY=your-key\n"
                "2. Create a .env file with: OPENAI_API_KEY=your-key"
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("GENERAL_MODEL", "gpt-4o")
        
        logger.info(f"LLM Client initialized with model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation (0-2)
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            Generated text
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            # Handle o3 model completely different API
            if self.model == "o3" or self.model == "o3-mini":
                # o3 uses a different API structure
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "text"},
                    reasoning_effort="medium" if self.model == "o3" else "low"
                )
                
                return response.choices[0].message.content
            else:
                # Standard API for gpt-4, gpt-3.5, etc.
                api_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                }
                
                response = self.client.chat.completions.create(**api_kwargs)
                
                return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise
    
    def generate_with_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate JSON response.
        
        Uses response_format to ensure JSON output.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            Parsed JSON response
        """
        # Add JSON instruction to prompts
        if system_prompt:
            system_prompt += "\nAlways respond with valid JSON."
        else:
            system_prompt = "Always respond with valid JSON."
        
        prompt += "\n\nRespond with JSON format."
        
        # For models that support response_format (but not o3 which has different API)
        if "gpt-4" in self.model or "gpt-3.5" in self.model:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response: {response}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        # For more accuracy, use tiktoken
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except:
            # Fallback to simple estimation
            return len(text) // 4