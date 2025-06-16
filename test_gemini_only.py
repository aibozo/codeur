#!/usr/bin/env python3
"""Test just Gemini to debug the issue."""

import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm import LLMClient

try:
    print("Creating LLMClient for Gemini...")
    client = LLMClient(model="gemini-2.5-flash", agent_name="test")
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