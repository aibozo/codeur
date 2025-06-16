"""
Test unified LLM provider system.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from src.llm_v2 import UnifiedLLMClient
from src.llm_providers.base import Message, CompletionResponse, GenerationConfig
from src.core.model_cards import ModelProvider


class TestUnifiedProviders:
    """Test the unified provider system."""
    
    def test_provider_selection(self):
        """Test that correct provider is selected based on model."""
        # Test OpenAI model
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="gpt-4o")
            assert client.model_card.provider == ModelProvider.OPENAI
            assert client.model == "gpt-4o"
        
        # Test Google model
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="gemini-2.0-flash")
            assert client.model_card.provider == ModelProvider.GOOGLE
            assert client.model == "gemini-2.0-flash"
        
        # Test Anthropic model
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="claude-opus-4")
            assert client.model_card.provider == ModelProvider.ANTHROPIC
            assert client.model == "claude-opus-4"
    
    def test_model_requirements(self):
        """Test that model-specific requirements are applied."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="claude-opus-4")
            
            # Claude requires max_tokens
            config = GenerationConfig(temperature=0.5)
            client._apply_model_requirements(config)
            assert config.max_tokens is not None
            assert config.max_tokens <= 4096
    
    def test_temperature_clamping(self):
        """Test temperature is clamped to valid range."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="claude-opus-4")
            
            # Claude has 0-1 temperature range
            config = GenerationConfig(temperature=1.5)
            client._apply_model_requirements(config)
            assert config.temperature == 1.0
    
    def test_json_generation(self):
        """Test JSON generation handling."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="gpt-4o")
            
            # Mock the provider's generate method
            mock_response = CompletionResponse(
                content='{"task": "test", "status": "completed"}',
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            )
            
            with patch.object(client.provider, 'generate', return_value=mock_response):
                result = client.generate_json(
                    prompt="Create a test task",
                    system_prompt="You are a helpful assistant"
                )
                
                assert isinstance(result, dict)
                assert result["task"] == "test"
                assert result["status"] == "completed"
    
    def test_cost_tracking(self):
        """Test that costs are tracked correctly."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = UnifiedLLMClient(model="gpt-4o", agent_name="test_agent")
            
            # Reset cost tracker
            client.cost_tracker.reset()
            
            # Mock response with usage
            mock_response = CompletionResponse(
                content="Test response",
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            )
            
            with patch.object(client.provider, 'generate', return_value=mock_response):
                client.generate("Test prompt")
            
            # Check cost summary
            summary = client.get_cost_summary()
            assert summary["agent"] == "test_agent"
            assert summary["model"] == "GPT-4o"
            assert summary["total_cost"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])