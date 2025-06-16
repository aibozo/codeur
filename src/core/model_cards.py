"""
Model cards system for unified model management and cost tracking.

This module provides a centralized registry of available LLM models with their
pricing, limits, and capabilities. It enables cost tracking and helps agents
select appropriate models based on requirements.
"""

from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import os


class ModelProvider(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


@dataclass
class ModelCard:
    """
    Model card containing pricing, limits, and capabilities.
    
    All prices are in USD per 1M tokens unless otherwise specified.
    """
    provider: ModelProvider
    model_id: str  # API model name
    display_name: str  # Human-readable name
    input_price: float  # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    context_window: int  # Maximum context length in tokens
    max_output_tokens: int  # Maximum output tokens
    features: List[str] = field(default_factory=list)  # Key features
    additional_costs: Dict[str, str] = field(default_factory=dict)  # Tool-specific costs
    supports_tools: bool = True  # Whether model supports function calling
    supports_vision: bool = False  # Whether model supports image inputs
    supports_json_mode: bool = True  # Whether model supports JSON response format
    temperature_range: Tuple[float, float] = (0.0, 2.0)  # Valid temperature range
    supports_streaming: bool = True  # Whether model supports streaming responses
    supports_system_messages: bool = True  # Whether model supports system messages
    requires_max_tokens: bool = False  # Whether max_tokens is required (e.g., Claude)
    special_requirements: Dict[str, Any] = field(default_factory=dict)  # Provider-specific requirements
    
    @property
    def cost_per_1k_input(self) -> float:
        """Cost per 1K input tokens."""
        return self.input_price / 1000
    
    @property
    def cost_per_1k_output(self) -> float:
        """Cost per 1K output tokens."""
        return self.output_price / 1000
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a specific usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.input_price
        output_cost = (output_tokens / 1_000_000) * self.output_price
        return input_cost + output_cost


# Model Registry
MODEL_CARDS: Dict[str, ModelCard] = {
    # OpenAI Models
    "o3": ModelCard(
        provider=ModelProvider.OPENAI,
        model_id="o3",  # Placeholder - actual API name TBD
        display_name="OpenAI o3",
        input_price=2.00,
        output_price=8.00,
        context_window=200_000,
        max_output_tokens=16_384,
        features=["SOTA reasoning", "vision", "tools"],
        additional_costs={
            "web_search": "$35-$50/1k calls",
            "file_search": "$2.50/1k calls + $0.10/GB/day storage",
            "computer_use": "$3/$12 per 1M tokens"
        },
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=False,  # o3 doesn't support JSON mode
        special_requirements={
            "no_temperature": True,  # o3 doesn't support temperature
            "reasoning_effort": ["low", "medium", "high"]
        }
    ),
    
    "o4-mini": ModelCard(
        provider=ModelProvider.OPENAI,
        model_id="o4-mini",  # Placeholder - actual API name TBD
        display_name="OpenAI o4-mini",
        input_price=1.10,
        output_price=4.40,
        context_window=200_000,
        max_output_tokens=16_384,
        features=["fast", "cost-efficient", "reasoning", "tool use"],
        supports_tools=True,
        supports_json_mode=True
    ),
    
    "gpt-4o": ModelCard(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o",
        display_name="GPT-4o",
        input_price=2.50,
        output_price=10.00,
        context_window=128_000,
        max_output_tokens=16_384,
        features=["flagship", "multimodal", "balanced"],
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=True
    ),
    
    "o1-pro": ModelCard(
        provider=ModelProvider.OPENAI,
        model_id="o1-pro",  # Placeholder - actual API name TBD
        display_name="OpenAI o1-pro",
        input_price=150.00,
        output_price=600.00,
        context_window=128_000,
        max_output_tokens=32_768,
        features=["ultra-premium", "complex agentic workflows"],
        supports_tools=True,
        supports_json_mode=True
    ),
    
    # Google Models
    "gemini-2.5-pro": ModelCard(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-pro",  # Placeholder - actual API name TBD
        display_name="Gemini 2.5 Pro",
        input_price=2.50,  # Varies 1.25-2.50 based on prompt size
        output_price=10.00,  # Varies 10.00-15.00
        context_window=2_000_000,
        max_output_tokens=8_192,
        features=["SOTA multimodal", "massive context", "reasoning"],
        additional_costs={
            "grounding_search": "$35/1k requests"
        },
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=True
    ),
    
    "gemini-2.5-flash": ModelCard(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-1.5-flash",  # Current API name for Gemini 1.5 Flash
        display_name="Gemini 2.5 Flash",
        input_price=0.15,
        output_price=0.60,  # Non-thinking mode; thinking mode is $3.50
        context_window=1_000_000,
        max_output_tokens=8_192,
        features=["fast", "efficient", "thinking mode"],
        additional_costs={
            "thinking_mode_output": "$3.50/1M tokens"
        },
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=True
    ),
    
    "gemini-2.0-flash": ModelCard(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        input_price=0.10,  # Text/image/video
        output_price=0.40,
        context_window=1_048_576,
        max_output_tokens=8_192,
        features=["balanced", "multimodal", "agents"],
        additional_costs={
            "audio_input": "$0.70/1M tokens",
            "context_caching": "$0.025/1M tokens (text/image/video)",
            "context_caching_audio": "$0.175/1M tokens",
            "context_caching_storage": "$1.00/1M tokens/hour",
            "image_generation": "$0.039/image",
            "grounding_search": "$35/1k requests (after 1500 free)",
            "live_api_text_input": "$0.35/1M tokens",
            "live_api_audio_input": "$2.10/1M tokens",
            "live_api_text_output": "$1.50/1M tokens",
            "live_api_audio_output": "$8.50/1M tokens"
        },
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=True
    ),
    
    # Gemini 2.5 Flash Native Audio - Voice/Dialog models
    "gemini-2.5-flash-preview-native-audio-dialog": ModelCard(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-flash-preview-native-audio-dialog",
        display_name="Gemini 2.5 Flash Native Audio Dialog",
        input_price=0.15,  # Text input price
        output_price=0.60,  # Text output price
        context_window=128_000,
        max_output_tokens=8_000,
        features=["native audio", "dialog", "voice interaction", "conversational"],
        additional_costs={
            "audio_input": "$0.70/1M tokens",
            "audio_output": "$3.00/1M tokens",
            "live_api": "See Live API pricing"
        },
        supports_tools=True,
        supports_vision=True,  # Supports video input
        supports_json_mode=False,  # Structured outputs not supported
        supports_streaming=True,
        special_requirements={
            "api_type": "live",  # Uses Live API
            "supported_inputs": ["audio", "video", "text"],
            "supported_outputs": ["audio", "text"],
            "caching": False,
            "code_execution": False,
            "structured_outputs": False
        }
    ),
    
    "gemini-2.5-flash-exp-native-audio-thinking-dialog": ModelCard(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-flash-exp-native-audio-thinking-dialog",
        display_name="Gemini 2.5 Flash Native Audio Thinking Dialog",
        input_price=0.15,  # Text input price
        output_price=3.50,  # Thinking mode output price
        context_window=128_000,
        max_output_tokens=8_000,
        features=["native audio", "dialog", "thinking mode", "voice interaction", "conversational"],
        additional_costs={
            "audio_input": "$0.70/1M tokens",
            "audio_output": "$3.00/1M tokens",
            "thinking_output": "$3.50/1M tokens",
            "live_api": "See Live API pricing"
        },
        supports_tools=True,
        supports_vision=True,  # Supports video input
        supports_json_mode=False,  # Structured outputs not supported
        supports_streaming=True,
        special_requirements={
            "api_type": "live",  # Uses Live API
            "thinking_mode": True,
            "supported_inputs": ["audio", "video", "text"],
            "supported_outputs": ["audio", "text"],
            "caching": False,
            "code_execution": False,
            "structured_outputs": False,
            "model_version": "gemini-2.5-flash-exp-native-audio-thinking-dialog"
        }
    ),
    
    # Anthropic Models
    "claude-opus-4": ModelCard(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-opus-4",  # Placeholder - actual API name TBD
        display_name="Claude Opus 4",
        input_price=15.00,
        output_price=75.00,
        context_window=200_000,
        max_output_tokens=4_096,
        features=["SOTA coding", "complex agentic tasks", "AI safety"],
        additional_costs={
            "web_search": "$10/1k searches",
            "code_execution": "$0.05/hr"
        },
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=False,  # Claude doesn't have native JSON mode
        temperature_range=(0.0, 1.0),  # Claude uses 0-1 range
        requires_max_tokens=True,  # Claude requires max_tokens parameter
        supports_system_messages=True
    ),
    
    "claude-sonnet-4": ModelCard(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4",  # Placeholder - actual API name TBD
        display_name="Claude Sonnet 4",
        input_price=3.00,
        output_price=15.00,
        context_window=200_000,
        max_output_tokens=4_096,
        features=["balanced", "high performance", "accessible"],
        supports_vision=True,
        supports_tools=True,
        supports_json_mode=False,
        temperature_range=(0.0, 1.0)
    ),
}


# Model aliases for common use cases
MODEL_ALIASES = {
    "fast": "gemini-2.0-flash",
    "balanced": "gpt-4o",
    "powerful": "claude-opus-4",
    "budget": "gemini-2.5-flash",
    "premium": "o1-pro",
    "reasoning": "o3",
    "voice": "gemini-2.5-flash-preview-native-audio-dialog",
    "voice-thinking": "gemini-2.5-flash-exp-native-audio-thinking-dialog",
}


class ModelSelector:
    """Helper class for selecting appropriate models based on requirements."""
    
    @staticmethod
    def get_model_card(model_name: str) -> Optional[ModelCard]:
        """
        Get model card by name or alias.
        
        Args:
            model_name: Model ID or alias
            
        Returns:
            ModelCard if found, None otherwise
        """
        # Check direct model ID
        if model_name in MODEL_CARDS:
            return MODEL_CARDS[model_name]
        
        # Check aliases
        if model_name in MODEL_ALIASES:
            return MODEL_CARDS.get(MODEL_ALIASES[model_name])
        
        return None
    
    @staticmethod
    def get_models_by_provider(provider: ModelProvider) -> List[ModelCard]:
        """Get all models from a specific provider."""
        return [
            card for card in MODEL_CARDS.values()
            if card.provider == provider
        ]
    
    @staticmethod
    def get_models_within_budget(
        max_input_price: float,
        max_output_price: float
    ) -> List[ModelCard]:
        """Get models within a price budget."""
        return [
            card for card in MODEL_CARDS.values()
            if card.input_price <= max_input_price
            and card.output_price <= max_output_price
        ]
    
    @staticmethod
    def get_models_with_context(min_context: int) -> List[ModelCard]:
        """Get models with minimum context window."""
        return [
            card for card in MODEL_CARDS.values()
            if card.context_window >= min_context
        ]
    
    @staticmethod
    def get_model_for_agent(agent_type: str) -> Optional[ModelCard]:
        """
        Get recommended model for a specific agent type.
        
        Uses the unified agent configuration system.
        """
        from src.core.agent_config import AgentConfigManager
        
        # Get model from agent config (which checks env vars too)
        model_name = AgentConfigManager.get_model_for_agent(agent_type)
        return ModelSelector.get_model_card(model_name)


class CostTracker:
    """Track LLM usage costs across the system."""
    
    def __init__(self):
        self.usage_log: List[Dict] = []
        self.total_cost = 0.0
        self.cost_by_agent: Dict[str, float] = {}
        self.cost_by_model: Dict[str, float] = {}
    
    def track_usage(
        self,
        agent_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        additional_costs: float = 0.0
    ) -> float:
        """
        Track usage and calculate cost.
        
        Args:
            agent_name: Name of the agent using the model
            model_name: Model ID or alias
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            additional_costs: Any additional costs (e.g., tool usage)
            
        Returns:
            Total cost for this usage
        """
        card = ModelSelector.get_model_card(model_name)
        if not card:
            raise ValueError(f"Unknown model: {model_name}")
        
        # Calculate base cost
        cost = card.estimate_cost(input_tokens, output_tokens)
        cost += additional_costs
        
        # Log usage
        self.usage_log.append({
            "agent": agent_name,
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": self._get_timestamp()
        })
        
        # Update totals
        self.total_cost += cost
        self.cost_by_agent[agent_name] = self.cost_by_agent.get(agent_name, 0) + cost
        self.cost_by_model[model_name] = self.cost_by_model.get(model_name, 0) + cost
        
        return cost
    
    def get_summary(self) -> Dict:
        """Get usage summary."""
        return {
            "total_cost": self.total_cost,
            "cost_by_agent": self.cost_by_agent,
            "cost_by_model": self.cost_by_model,
            "usage_count": len(self.usage_log)
        }
    
    def reset(self):
        """Reset tracking data."""
        self.usage_log.clear()
        self.total_cost = 0.0
        self.cost_by_agent.clear()
        self.cost_by_model.clear()
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Global cost tracker instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker