#!/usr/bin/env python3
"""
Simulate voice agent tool calling without audio
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.voice_agent.gemini_live_tools import LiveVoiceAgent
from google import genai
from google.genai import types


async def simulate_tool_calling():
    """Simulate tool calling with the Live API."""
    print("Simulating Voice Agent Tool Calling")
    print("=" * 50)
    
    # Initialize client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    # Create function declarations
    search_code_decl = {
        "name": "search_code",
        "description": "Search for code in the codebase",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
    
    # Create config with tools
    config = types.GenerateContentConfig(
        tools=[{"function_declarations": [search_code_decl]}]
    )
    
    # Test with a query that should trigger tool use
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents="Search the codebase for EventBridge class implementation",
        config=config
    )
    
    # Check if function was called
    if response.candidates[0].content.parts[0].function_call:
        fc = response.candidates[0].content.parts[0].function_call
        print(f"✅ Function called: {fc.name}")
        print(f"   Arguments: {fc.args}")
        
        # Simulate function execution
        if fc.name == "search_code":
            print(f"\n🔍 Simulating search for: {fc.args.get('query')}")
            mock_result = {
                "results": [
                    {
                        "file": "src/core/event_bridge.py",
                        "line": 15,
                        "content": "class EventBridge: # Main event handling system"
                    }
                ],
                "count": 1
            }
            
            # Send function result back
            function_response = types.Part.from_function_response(
                name=fc.name,
                response=mock_result
            )
            
            # Get final response
            final_response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    response.candidates[0].content,
                    types.Content(role="user", parts=[function_response])
                ],
                config=config
            )
            
            print(f"\n🤖 Final response: {final_response.text}")
    else:
        print("❌ No function call detected")
        print(f"Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(simulate_tool_calling())