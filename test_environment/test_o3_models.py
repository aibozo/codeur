#!/usr/bin/env python3
"""
Test o3 models with different API formats.
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

def test_o3_mini():
    """Test o3-mini model."""
    print("=== Testing o3-mini ===\n")
    
    # Try different API formats
    formats = [
        {
            "name": "Standard format",
            "params": {
                "model": "o3-mini",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
            }
        },
        {
            "name": "With reasoning_effort",
            "params": {
                "model": "o3-mini",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "reasoning_effort": "low"
            }
        },
        {
            "name": "With response_format",
            "params": {
                "model": "o3-mini",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "response_format": {"type": "text"},
                "reasoning_effort": "low"
            }
        }
    ]
    
    for fmt in formats:
        print(f"\nTrying {fmt['name']}...")
        try:
            response = client.chat.completions.create(**fmt['params'])
            print(f"✓ Success! Response: {response.choices[0].message.content[:100]}")
            print(f"  Usage: {response.usage}")
            return True
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    return False


def test_gpt4():
    """Test GPT-4 as baseline."""
    print("\n=== Testing GPT-4 ===\n")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "What is 2+2?"}],
            max_tokens=10
        )
        print(f"✓ Success! Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


if __name__ == "__main__":
    # Test GPT-4 first
    test_gpt4()
    
    # Then test o3
    test_o3_mini()