"""
LLM Providers Package.

This package provides unified interfaces for working with multiple LLM providers:
- OpenAI (GPT-4, o1, o3 series)
- Google (Gemini series)
- Anthropic (Claude series)
"""

from .base import LLMProvider, Message, CompletionResponse, GenerationConfig, ResponseFormat
from .factory import ProviderFactory
from .openai_provider import OpenAIProvider
from .google_provider_v2 import GoogleProviderV2

# Conditional import for Anthropic
try:
    from .anthropic_provider import AnthropicProvider
    ANTHROPIC_AVAILABLE = True
except ImportError:
    AnthropicProvider = None
    ANTHROPIC_AVAILABLE = False

__all__ = [
    "LLMProvider",
    "Message",
    "CompletionResponse",
    "GenerationConfig",
    "ResponseFormat",
    "ProviderFactory",
    "OpenAIProvider",
    "GoogleProviderV2",
]

if ANTHROPIC_AVAILABLE:
    __all__.append("AnthropicProvider")