#!/usr/bin/env python3
"""
Test LLM client with Gemini.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from src.llm import LLMClient

print("Testing LLM client with Gemini...")
print("=" * 60)

try:
    # Initialize LLM client with Gemini model
    llm = LLMClient(model="gemini-2.5-flash", agent_name="test")
    
    print(f"✅ LLM client initialized")
    print(f"Model: {llm.model}")
    print(f"Provider: {llm.model_card.provider}")
    
    # Test generation
    print("\nTesting generation...")
    result = llm.generate(
        prompt="Say 'Hello' in one word",
        temperature=0.1
    )
    
    print(f"✅ Success!")
    print(f"Result: {result}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()