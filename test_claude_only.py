#!/usr/bin/env python3
"""Test just Claude to debug the issue."""

import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# First check if anthropic is available
try:
    import anthropic
    print("✅ anthropic module is installed")
except ImportError as e:
    print(f"❌ anthropic module not installed: {e}")
    print("Install with: pip install anthropic")
    sys.exit(1)

# Check API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    print(f"✅ ANTHROPIC_API_KEY is set (length: {len(api_key)})")
else:
    print("❌ ANTHROPIC_API_KEY not set")
    sys.exit(1)

# Try to create LLMClient
from src.llm import LLMClient

try:
    print("\nCreating LLMClient for Claude...")
    client = LLMClient(model="claude-sonnet-4", agent_name="test")
    print(f"✅ Client created: {client.model_card.display_name}")
    
    print("\nTesting generate method...")
    response = client.generate(
        prompt="Hello, what model are you?",
        system_prompt="You are a helpful assistant. Be concise."
    )
    print(f"✅ Response: {response}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()