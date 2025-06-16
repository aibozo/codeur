"""
LLM Provider Factory.

This module provides a factory for creating the appropriate LLM provider
based on the model or provider name.
"""

import logging
from typing import Optional, Dict, Type
from enum import Enum

from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .google_provider_v2 import GoogleProviderV2
from .anthropic_provider import AnthropicProvider
from ..core.model_cards import ModelProvider, ModelSelector

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating LLM providers."""
    
    # Provider mapping
    _providers: Dict[ModelProvider, Type[LLMProvider]] = {
        ModelProvider.OPENAI: OpenAIProvider,
        ModelProvider.GOOGLE: GoogleProviderV2,
        ModelProvider.ANTHROPIC: AnthropicProvider
    }
    
    # Cache for provider instances
    _instances: Dict[ModelProvider, LLMProvider] = {}
    
    @classmethod
    def get_provider(cls, model_name: str) -> LLMProvider:
        """
        Get the appropriate provider for a model.
        
        Args:
            model_name: Model name or ID
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If model is not found or provider not supported
        """
        # Get model card
        model_card = ModelSelector.get_model_card(model_name)
        if not model_card:
            raise ValueError(f"Unknown model: {model_name}")
        
        # Check cache
        if model_card.provider in cls._instances:
            return cls._instances[model_card.provider]
        
        # Create new provider
        provider_class = cls._providers.get(model_card.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {model_card.provider}")
        
        try:
            provider = provider_class()
            cls._instances[model_card.provider] = provider
            logger.info(f"Created {model_card.provider.value} provider for {model_name}")
            return provider
        except Exception as e:
            logger.error(f"Failed to create provider: {e}")
            raise
    
    @classmethod
    def get_provider_for_enum(cls, provider: ModelProvider) -> LLMProvider:
        """
        Get provider instance by enum.
        
        Args:
            provider: ModelProvider enum
            
        Returns:
            LLMProvider instance
        """
        if provider in cls._instances:
            return cls._instances[provider]
        
        provider_class = cls._providers.get(provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {provider}")
        
        provider_instance = provider_class()
        cls._instances[provider] = provider_instance
        return provider_instance
    
    @classmethod
    def clear_cache(cls):
        """Clear cached provider instances."""
        cls._instances.clear()
        logger.info("Cleared provider cache")
    
    @classmethod
    def register_provider(cls, provider_enum: ModelProvider, provider_class: Type[LLMProvider]):
        """
        Register a custom provider.
        
        Args:
            provider_enum: Provider enum value
            provider_class: Provider class
        """
        cls._providers[provider_enum] = provider_class
        logger.info(f"Registered custom provider: {provider_enum.value}")