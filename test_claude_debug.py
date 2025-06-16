#!/usr/bin/env python3
"""Debug Claude API issues."""

import os
import sys
import logging
from dotenv import load_dotenv

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test raw anthropic client first
print("Testing raw Anthropic client...")
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Try the exact model from the docs
    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello, Claude"}
        ]
    )
    print(f"✅ Raw client works! Response: {response.content[0].text}")
    
except Exception as e:
    print(f"❌ Raw client failed: {e}")
    import traceback
    traceback.print_exc()

# Now test our provider
print("\n\nTesting our AnthropicProvider...")
try:
    from src.llm_providers.anthropic_provider import AnthropicProvider
    from src.llm_providers.base import Message, GenerationConfig
    
    provider = AnthropicProvider()
    messages = [Message(role="user", content="Hello, Claude")]
    config = GenerationConfig(max_tokens=1024)
    
    response = provider.generate(
        messages=messages,
        model="claude-opus-4-20250514",
        config=config
    )
    print(f"✅ Provider works! Response: {response.content}")
    
except Exception as e:
    print(f"❌ Provider failed: {e}")
    import traceback
    traceback.print_exc()

# Finally test LLMClient
print("\n\nTesting LLMClient...")
try:
    from src.llm import LLMClient
    
    client = LLMClient(model="claude-opus-4", agent_name="test")
    response = client.generate(
        prompt="Hello, Claude",
        system_prompt="You are a helpful assistant."
    )
    print(f"✅ LLMClient works! Response: {response}")
    
except Exception as e:
    print(f"❌ LLMClient failed: {e}")
    import traceback
    traceback.print_exc()