#!/usr/bin/env python3
"""Debug Gemini response issue"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

from src.llm import LLMClient

async def test_gemini():
    # Create LLM client
    client = LLMClient(agent_name="test")
    
    # Simple prompt
    prompt = "Create a simple Python calculator class with add and subtract methods. Respond with just the code."
    
    # System prompt
    system_prompt = "You are a helpful coding assistant. Provide clean, working code."
    
    print("Testing Gemini with simple prompt...")
    print(f"Prompt: {prompt}")
    print(f"System prompt: {system_prompt}")
    
    try:
        response = client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=500
        )
        
        print(f"\nResponse length: {len(response)} chars")
        print(f"Response: {response[:200]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini())