#!/usr/bin/env python3
"""
Test simple Live API without tools
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types


async def test_simple_live():
    """Test basic Live API connection."""
    print("Testing Simple Live API Connection")
    print("=" * 50)
    
    # Initialize client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    # Simple config without tools
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],  # Text only for testing
    )
    
    MODEL = "models/gemini-2.5-flash-preview-native-audio-dialog"
    
    print(f"Connecting to {MODEL}...")
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected successfully!")
            
            # Send a simple message
            await session.send_client_content(
                turns=[{"parts": [{"text": "Hello! Please respond with just text."}]}],
                turn_complete=True
            )
            
            print("\nWaiting for response...")
            
            # Receive response
            turn = session.receive()
            async for response in turn:
                if hasattr(response, 'text') and response.text:
                    print(f"Response: {response.text}")
                elif hasattr(response, 'parts'):
                    for part in response.parts:
                        if hasattr(part, 'text') and part.text:
                            print(f"Response: {part.text}")
            
            print("\n✅ Basic connection works!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_live())