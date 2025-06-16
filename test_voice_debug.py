#!/usr/bin/env python3
"""
Debug voice agent tool configuration
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

from google import genai
from google.genai import types


async def debug_live_api():
    """Debug Live API configuration."""
    print("Debugging Live API Tool Configuration")
    print("=" * 50)
    
    # Initialize client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    # Simple function declaration
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
    
    # Configure with tools
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO", "TEXT"],  # Allow both
        tools=[
            {"function_declarations": [search_code_decl]}
        ]
    )
    
    print("Connecting to Live API with tools...")
    
    try:
        async with client.aio.live.connect(
            model="models/gemini-2.5-flash-preview-native-audio-dialog",  # Use audio model
            config=config
        ) as session:
            print("✅ Connected successfully!")
            
            # Send initial message
            await session.send_client_content(
                turns=[{"parts": [{"text": "Hello! Can you search for EventBridge in the codebase?"}]}],
                turn_complete=True
            )
            
            print("\nWaiting for response...")
            
            # Receive one turn
            turn = session.receive()
            async for response in turn:
                print(f"\nResponse received: {type(response)}")
                
                # Check what's in the response
                if hasattr(response, 'parts'):
                    print(f"Parts found: {len(response.parts)}")
                    for i, part in enumerate(response.parts):
                        print(f"\nPart {i}:")
                        if hasattr(part, 'text'):
                            print(f"  Text: {part.text[:100]}...")
                        if hasattr(part, 'function_call'):
                            print(f"  Function call: {part.function_call}")
                        if hasattr(part, 'thought'):
                            print(f"  Thought: {part.thought[:100]}...")
                
                # Old format check
                if hasattr(response, 'text') and response.text:
                    print(f"Direct text: {response.text[:100]}...")
                if hasattr(response, 'function_call') and response.function_call:
                    print(f"Direct function call: {response.function_call}")
            
            print("\n✅ Test complete!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_live_api())