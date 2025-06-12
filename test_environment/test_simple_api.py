#!/usr/bin/env python3
"""
Simple API test with the loaded key.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load from parent .env
load_dotenv(Path(__file__).parent.parent / ".env")

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI

# Verify key is loaded
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded: {api_key[:7]}...{api_key[-4:]}")

# Test with simple API call
client = OpenAI(api_key=api_key)

try:
    # Try a simple completion with gpt-3.5-turbo
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'test'"}],
        max_tokens=10
    )
    print(f"\nAPI works! Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"\nAPI Error: {e}")
    
    # Try listing models to check if API key has any access
    try:
        models = client.models.list()
        print("\nAPI key is valid but may have limited permissions.")
        print("Available models:", [m.id for m in models.data[:5]])
    except Exception as e2:
        print(f"\nCannot list models either: {e2}")
        print("\nThe API key appears to be invalid or expired.")