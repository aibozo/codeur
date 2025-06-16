#!/usr/bin/env python3
"""
Test LLM client with Gemini without retries.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from src.llm_providers.google_provider import GoogleProvider

print("Testing Google provider directly without retries...")
print("=" * 60)

try:
    provider = GoogleProvider()
    
    messages = [{"role": "user", "content": "Say 'Hello' in one word"}]
    
    response = provider.create_completion(
        model_id="gemini-2.5-flash-preview-05-20",
        messages=messages,
        temperature=0.1
    )
    
    print(f"✅ Success!")
    print(f"Response: {response}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()