#!/usr/bin/env python3
"""
Debug Google provider to see what's happening.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from src.llm_providers.google_provider import GoogleProvider

# Test the provider
provider = GoogleProvider()

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Say 'Hello' in one word"}
]

print("Testing Google provider...")
print("=" * 60)

try:
    response = provider.create_completion(
        model_id="gemini-2.5-flash-preview-05-20",
        messages=messages,
        temperature=0.1
    )
    
    print(f"✅ Success!")
    print(f"Response: {response}")
    print(f"Content: {response.get('content', 'NO CONTENT')}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting with simple message...")
try:
    response = provider.create_completion(
        model_id="gemini-2.5-flash-preview-05-20",
        messages=[{"role": "user", "content": "What is 2+2?"}],
        temperature=0.1
    )
    
    print(f"✅ Success!")
    print(f"Content: {response.get('content', 'NO CONTENT')}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()