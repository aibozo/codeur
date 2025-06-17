"""
Shared LLM client for all agents.

Provides a simple interface for generating text with OpenAI models.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# Note: ResilientLLMClient should be imported directly from src.core.resilient_llm
# to avoid circular imports
from src.core.model_cards import ModelSelector, get_cost_tracker, ModelProvider

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Generic LLM client for text generation.
    
    Can be used by any agent for generating code, text, or other content.
    """
    
    def __init__(self, model: Optional[str] = None, agent_name: str = "general"):
        """
        Initialize the LLM client.
        
        Args:
            model: Model to use (defaults to GENERAL_MODEL env var or gpt-4o)
            agent_name: Name of the agent using this client (for cost tracking)
        """
        self.agent_name = agent_name
        
        # Get model card
        if model:
            self.model_card = ModelSelector.get_model_card(model)
            if not self.model_card:
                logger.warning(f"Unknown model {model}, falling back to default")
                self.model_card = ModelSelector.get_model_for_agent(agent_name)
        else:
            # Try agent-specific model first
            self.model_card = ModelSelector.get_model_for_agent(agent_name)
        
        if not self.model_card:
            raise ValueError("No model card found for the specified model")
        
        self.model = self.model_card.model_id
        
        # Initialize appropriate client based on provider
        if self.model_card.provider == ModelProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable not set.\n"
                    "Please either:\n"
                    "1. Export it: export OPENAI_API_KEY=your-key\n"
                    "2. Create a .env file with: OPENAI_API_KEY=your-key"
                )
            self.client = OpenAI(api_key=api_key)
        elif self.model_card.provider == ModelProvider.GOOGLE:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            try:
                from src.llm_providers.google_provider_v2 import GoogleProviderV2
                self.client = GoogleProviderV2(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "Google Generative AI library not installed.\n"
                    "Install with: pip install google-generativeai"
                )
        elif self.model_card.provider == ModelProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            try:
                from src.llm_providers.anthropic_provider import AnthropicProvider
                self.client = AnthropicProvider(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic library not installed.\n"
                    "Install with: pip install anthropic"
                )
        
        # Initialize cost tracker
        self.cost_tracker = get_cost_tracker()
        
        logger.info(f"LLM Client initialized with model: {self.model_card.display_name} ({self.model})")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate (uses model default if not specified)
            temperature: Temperature for generation (uses model default if not specified)
            **kwargs: Additional API parameters
            
        Returns:
            Generated text
        """
        # Use model card defaults if not specified
        if max_tokens is None:
            max_tokens = self.model_card.max_output_tokens
        else:
            max_tokens = min(max_tokens, self.model_card.max_output_tokens)
        
        if temperature is None:
            temperature = 0.2
        else:
            # Clamp temperature to model's valid range
            min_temp, max_temp = self.model_card.temperature_range
            temperature = max(min_temp, min(temperature, max_temp))
        
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
        
        # Count input tokens for cost tracking
        input_tokens = self.count_tokens(prompt)
        if system_prompt:
            input_tokens += self.count_tokens(system_prompt)
        
        try:
            # Provider-specific API calls
            if self.model_card.provider == ModelProvider.OPENAI:
                # Handle o3 model completely different API
                if self.model == "o3" or self.model == "o3-mini":
                    # o3 uses a different API structure
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "text"},
                        reasoning_effort="medium" if self.model == "o3" else "low"
                    )
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
                
                result = response.choices[0].message.content
                
                # Track token usage
                if hasattr(response, 'usage'):
                    output_tokens = response.usage.completion_tokens
                    input_tokens = response.usage.prompt_tokens
                else:
                    output_tokens = self.count_tokens(result)
                
                # Track cost
                self.cost_tracker.track_usage(
                    agent_name=self.agent_name,
                    model_name=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                
                return result
                
            elif self.model_card.provider == ModelProvider.GOOGLE:
                # Use Google provider V2
                from src.llm_providers.base import Message as ProviderMessage, GenerationConfig
                
                # Convert messages to provider format
                provider_messages = []
                for msg in messages:
                    provider_messages.append(ProviderMessage(
                        role=msg["role"],
                        content=msg["content"]
                    ))
                
                # Create config
                config = GenerationConfig(
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Generate response
                response = self.client.generate(
                    messages=provider_messages,
                    model=self.model,
                    config=config
                )
                
                result = response.content
                
                # Use actual token counts if available
                if response.usage:
                    input_tokens = response.usage.get('prompt_tokens', input_tokens)
                    output_tokens = response.usage.get('completion_tokens', self.count_tokens(result))
                else:
                    output_tokens = self.count_tokens(result)
                
                # Track cost
                self.cost_tracker.track_usage(
                    agent_name=self.agent_name,
                    model_name=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                
                return result
                
            elif self.model_card.provider == ModelProvider.ANTHROPIC:
                # Use Anthropic provider
                from src.llm_providers.base import Message as ProviderMessage, GenerationConfig
                
                # Convert messages to provider format
                provider_messages = []
                for msg in messages:
                    provider_messages.append(ProviderMessage(
                        role=msg["role"],
                        content=msg["content"]
                    ))
                
                # Create config with Claude's requirements
                config = GenerationConfig(
                    temperature=temperature,
                    max_tokens=max_tokens if max_tokens else self.model_card.max_output_tokens,  # Claude requires max_tokens
                    **kwargs
                )
                
                # Generate response
                response = self.client.generate(
                    messages=provider_messages,
                    model=self.model,
                    config=config
                )
                
                result = response.content
                
                # Use actual token counts if available
                if response.usage:
                    input_tokens = response.usage.get('prompt_tokens', input_tokens)
                    output_tokens = response.usage.get('completion_tokens', self.count_tokens(result))
                else:
                    output_tokens = self.count_tokens(result)
                
                # Track cost
                self.cost_tracker.track_usage(
                    agent_name=self.agent_name,
                    model_name=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                
                return result
                
            else:
                raise NotImplementedError(f"Provider {self.model_card.provider} not implemented")
            
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise
    
    def generate_with_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
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
        
        # For models that support response_format
        if self.model_card.supports_json_mode and self.model_card.provider == ModelProvider.OPENAI and self.model not in ["o3", "o3-mini"]:
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
            import re
            
            # Try to extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            
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
        # Provider-specific token counting
        if self.model_card.provider == ModelProvider.GOOGLE and hasattr(self.client, 'count_tokens'):
            try:
                return self.client.count_tokens(self.model, text)
            except:
                pass
        
        # OpenAI models with tiktoken
        if self.model_card.provider == ModelProvider.OPENAI:
            try:
                import tiktoken
                encoding = tiktoken.encoding_for_model(self.model)
                return len(encoding.encode(text))
            except:
                pass
        
        # Fallback to simple estimation
        return len(text) // 4
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for this agent."""
        summary = self.cost_tracker.get_summary()
        agent_cost = summary["cost_by_agent"].get(self.agent_name, 0.0)
        return {
            "agent": self.agent_name,
            "model": self.model_card.display_name,
            "total_cost": agent_cost,
            "model_info": {
                "input_price_per_1m": self.model_card.input_price,
                "output_price_per_1m": self.model_card.output_price,
                "context_window": self.model_card.context_window,
                "max_output": self.model_card.max_output_tokens
            }
        }