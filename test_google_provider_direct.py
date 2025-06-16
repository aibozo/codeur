#!/usr/bin/env python3
"""
Test Google provider directly to see the actual error.
"""

import os
from dotenv import load_dotenv
from src.llm_providers.google_provider import GoogleProvider

load_dotenv()

# Create provider
print("Creating Google provider...")
try:
    provider = GoogleProvider()
    print("✅ Provider created")
except Exception as e:
    print(f"❌ Failed to create provider: {e}")
    exit(1)

# Test with simple message
messages = [
    {"role": "user", "content": "Say hello in one word"}
]

models_to_test = [
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

for model in models_to_test:
    print(f"\nTesting model: {model}")
    try:
        response = provider.create_completion(
            model_id=model,
            messages=messages,
            temperature=0.1,
            max_tokens=10
        )
        print(f"✅ Success: {response['content']}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()