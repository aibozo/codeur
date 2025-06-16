"""
Unified LLM Client v2.

This module provides a clean, unified interface for working with multiple LLM providers
(OpenAI, Google, Anthropic) using the provider factory pattern.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Union

from .core.model_cards import ModelSelector, get_cost_tracker
from .llm_providers.base import Message, GenerationConfig, ResponseFormat
from .llm_providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


class UnifiedLLMClient:
    """
    Unified client for all LLM providers.
    
    This client automatically selects the appropriate provider based on the model
    and handles all provider-specific differences transparently.
    """
    
    def __init__(self, model: Optional[str] = None, agent_name: str = "general"):
        """
        Initialize the unified LLM client.
        
        Args:
            model: Model to use (defaults to GENERAL_MODEL env var)
            agent_name: Name of the agent using this client (for cost tracking)
        """
        self.agent_name = agent_name
        
        # Get model card
        if not model:
            model = os.getenv("GENERAL_MODEL", "gpt-4o")
        
        self.model_card = ModelSelector.get_model_card(model)
        if not self.model_card:
            raise ValueError(f"Unknown model: {model}")
        
        self.model = self.model_card.model_id
        
        # Get provider
        self.provider = ProviderFactory.get_provider(model)
        
        # Initialize cost tracker
        self.cost_tracker = get_cost_tracker()
        
        logger.info(
            f"Unified LLM Client initialized with model: {self.model_card.display_name} "
            f"({self.model}) via {self.model_card.provider.value}"
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            json_mode: Whether to request JSON output
            stop_sequences: Optional stop sequences
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text
        """
        # Build messages
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        # Build config
        config = GenerationConfig(
            temperature=temperature or 0.7,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            response_format=ResponseFormat.JSON if json_mode else ResponseFormat.TEXT
        )
        
        # Handle provider-specific requirements
        self._apply_model_requirements(config)
        
        # Generate
        response = self.provider.generate(messages, self.model, config)
        
        # Track costs
        if response.usage:
            self.cost_tracker.track_usage(
                agent_name=self.agent_name,
                model_name=self.model,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0)
            )
        
        return response.content
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate JSON response.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response
        """
        # Add JSON instruction to prompts
        if system_prompt:
            system_prompt += "\nAlways respond with valid JSON."
        else:
            system_prompt = "Always respond with valid JSON."
        
        prompt += "\n\nRespond with JSON format."
        
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=self.model_card.supports_json_mode,
            **kwargs
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response: {response}")
                raise
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """
        Generate streaming response.
        
        Yields partial responses as they arrive.
        """
        if not self.model_card.supports_streaming:
            raise ValueError(f"Model {self.model} does not support streaming")
        
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        config = GenerationConfig(
            temperature=temperature or 0.7,
            max_tokens=max_tokens
        )
        
        self._apply_model_requirements(config)
        
        # Stream responses
        for chunk in self.provider.generate_stream(messages, self.model, config):
            yield chunk
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return self.provider.count_tokens(text, self.model)
    
    def _apply_model_requirements(self, config: GenerationConfig):
        """Apply model-specific requirements to config."""
        # Handle Claude's max_tokens requirement
        if self.model_card.requires_max_tokens and not config.max_tokens:
            config.max_tokens = min(4096, self.model_card.max_output_tokens)
        
        # Handle temperature constraints
        if self.model_card.special_requirements.get("no_temperature"):
            config.temperature = None
        else:
            # Clamp temperature to valid range
            min_temp, max_temp = self.model_card.temperature_range
            if config.temperature is not None:
                config.temperature = max(min_temp, min(config.temperature, max_temp))
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for this agent."""
        summary = self.cost_tracker.get_summary()
        agent_cost = summary["cost_by_agent"].get(self.agent_name, 0.0)
        return {
            "agent": self.agent_name,
            "model": self.model_card.display_name,
            "total_cost": agent_cost,
            "model_info": {
                "provider": self.model_card.provider.value,
                "input_price_per_1m": self.model_card.input_price,
                "output_price_per_1m": self.model_card.output_price,
                "context_window": self.model_card.context_window,
                "max_output": self.model_card.max_output_tokens
            }
        }


# Backward compatibility alias
LLMClient = UnifiedLLMClient