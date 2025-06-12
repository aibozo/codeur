#!/usr/bin/env python3
"""
Test full o3 model.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load from parent .env
load_dotenv(Path(__file__).parent.parent / ".env")

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI

client = OpenAI()

def test_o3():
    """Test full o3 model."""
    print("=== Testing o3 (full model) ===\n")
    
    # Try different API formats
    formats = [
        {
            "name": "Standard format",
            "params": {
                "model": "o3",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
            }
        },
        {
            "name": "With reasoning_effort medium",
            "params": {
                "model": "o3",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "reasoning_effort": "medium"
            }
        },
        {
            "name": "With reasoning_effort high",
            "params": {
                "model": "o3",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "reasoning_effort": "high"
            }
        }
    ]
    
    for fmt in formats:
        print(f"\nTrying {fmt['name']}...")
        try:
            response = client.chat.completions.create(**fmt['params'])
            print(f"✓ Success! Response: {response.choices[0].message.content[:100]}")
            print(f"  Usage: {response.usage}")
            print(f"  Reasoning tokens: {response.usage.completion_tokens_details.reasoning_tokens}")
            return True
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    return False


if __name__ == "__main__":
    test_o3()