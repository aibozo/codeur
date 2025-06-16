#!/usr/bin/env python3
"""
Test following the exact Live API example from documentation
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types


async def test_basic_live_connection():
    """Test the most basic Live API connection."""
    print("Testing Basic Live API Connection")
    print("=" * 50)
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Use the exact model from the docs
    model = "gemini-2.0-flash-live"  # Try without the -001 suffix
    config = {"response_modalities": ["TEXT"]}
    
    try:
        print(f"Attempting to connect to: {model}")
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Session started successfully!")
            
            # Send a simple message
            message = "Hello, how are you?"
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": message}]}, 
                turn_complete=True
            )
            
            print(f"📤 Sent: {message}")
            print("⏳ Waiting for response...")
            
            # Receive response
            async for response in session.receive():
                if response.text is not None:
                    print(f"📥 Response: {response.text}")
                    break
                    
    except Exception as e:
        print(f"❌ Error with {model}: {e}")
        
        # Try alternative model names
        alt_models = [
            "gemini-2.0-flash-live-001",
            "models/gemini-2.0-flash-live",
            "models/gemini-2.0-flash-live-001",
            "gemini-2.5-flash-live",
            "models/gemini-2.5-flash-live"
        ]
        
        print("\nTrying alternative model names...")
        for alt_model in alt_models:
            try:
                print(f"\nTrying: {alt_model}")
                async with client.aio.live.connect(model=alt_model, config=config) as session:
                    print(f"✅ {alt_model} works!")
                    break
            except Exception as e:
                print(f"❌ {alt_model} failed: {str(e)[:50]}...")


async def test_audio_with_working_model():
    """Test audio with a model we know works."""
    print("\n\nTesting Audio with Working Model")
    print("=" * 50)
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Use the model that worked
    model = "models/gemini-2.0-flash-live-001"
    
    # Test different audio configurations
    configs = [
        {
            "name": "Simple audio-to-text",
            "config": {"response_modalities": ["TEXT"]}
        },
        {
            "name": "With VAD settings",
            "config": {
                "response_modalities": ["TEXT"],
                "realtime_input_config": {
                    "automatic_activity_detection": {
                        "disabled": False
                    }
                }
            }
        },
        {
            "name": "With input transcription",
            "config": {
                "response_modalities": ["TEXT"],
                "input_audio_transcription": {}
            }
        }
    ]
    
    for test_config in configs:
        print(f"\n🧪 Testing: {test_config['name']}")
        
        try:
            async with client.aio.live.connect(model=model, config=test_config['config']) as session:
                print("✅ Connected!")
                
                # Send a simple audio blob
                # Create 1 second of tone
                import numpy as np
                sample_rate = 16000
                duration = 1.0
                t = np.linspace(0, duration, int(sample_rate * duration))
                
                # Simple sine wave
                audio = np.sin(2 * np.pi * 440 * t)  # A4 note
                audio_bytes = (audio * 16384).astype(np.int16).tobytes()
                
                print(f"📤 Sending {len(audio_bytes)} bytes of audio...")
                
                # Send audio
                await session.send_realtime_input(
                    audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                )
                
                # Send stream end to force processing
                await session.send_realtime_input(audio_stream_end=True)
                
                print("⏳ Waiting 5 seconds for response...")
                
                # Wait for response with timeout
                import time
                start_time = time.time()
                got_response = False
                
                async for response in session.receive():
                    if response.text is not None:
                        print(f"📥 Got text: {response.text}")
                        got_response = True
                        break
                    
                    # Check for transcription
                    if hasattr(response, 'server_content') and response.server_content:
                        if hasattr(response.server_content, 'input_transcription'):
                            trans = response.server_content.input_transcription
                            if trans:
                                print(f"📝 Transcription: {trans.text}")
                                got_response = True
                    
                    if time.time() - start_time > 5:
                        print("⏱️ Timeout")
                        break
                
                if not got_response:
                    print("❌ No response received")
                    
        except Exception as e:
            print(f"❌ Error: {e}")


async def test_download_sample_audio():
    """Download and test with Google's sample audio file."""
    print("\n\nTesting with Google's Sample Audio")
    print("=" * 50)
    
    # Download sample file
    sample_url = "https://storage.googleapis.com/generativeai-downloads/data/hello_are_you_there.pcm"
    
    try:
        import urllib.request
        print(f"📥 Downloading sample from: {sample_url}")
        urllib.request.urlretrieve(sample_url, "sample.pcm")
        print("✅ Downloaded sample.pcm")
        
        # Load the audio
        audio_bytes = Path("sample.pcm").read_bytes()
        print(f"📊 Loaded {len(audio_bytes)} bytes")
        
        # Test with Live API
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model = "models/gemini-2.0-flash-live-001"
        config = {"response_modalities": ["TEXT"]}
        
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected!")
            
            print("📤 Sending Google's sample audio...")
            await session.send_realtime_input(
                audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
            )
            
            print("⏳ Waiting for response...")
            
            import time
            start_time = time.time()
            
            async for response in session.receive():
                if response.text is not None:
                    print(f"\n✅ SUCCESS! Transcription: {response.text}")
                    break
                    
                if time.time() - start_time > 10:
                    print("\n❌ Timeout - no transcription received")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🔍 GEMINI LIVE API - TROUBLESHOOTING TEST\n")
    
    asyncio.run(test_basic_live_connection())
    asyncio.run(test_audio_with_working_model())
    asyncio.run(test_download_sample_audio())