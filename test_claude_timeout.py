#!/usr/bin/env python3
"""Test Claude with explicit error handling."""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm import LLMClient

try:
    print("Creating LLMClient for Claude...")
    client = LLMClient(model="claude-opus-4", agent_name="test")
    print(f"✅ Client created: {client.model_card.display_name}")
    
    print("\nTesting generate method without retry decorator...")
    # Access the underlying generate method without retry
    start = time.time()
    
    # Call the generate method directly (with retries)
    try:
        response = client.generate.__wrapped__(
            client,
            prompt="Say 'Hello' in one word",
            system_prompt="You are a helpful assistant. Reply with just one word.",
            temperature=0.2,
            max_tokens=10
        )
        print(f"✅ Response: {response}")
    except Exception as e:
        print(f"❌ Direct error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    elapsed = time.time() - start
    print(f"Time taken: {elapsed:.2f}s")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()