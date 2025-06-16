#!/usr/bin/env python3
"""
Minimal test to isolate audio streaming issue
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types


async def test_text_only():
    """Verify text interaction works."""
    print("1. Testing Text-Only Interaction")
    print("=" * 50)
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "models/gemini-2.0-flash-live-001"
    config = {"response_modalities": ["TEXT"]}
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected!")
            
            # Send text
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Reply with just 'yes' if you can hear me"}]},
                turn_complete=True
            )
            
            # Get response
            async for response in session.receive():
                if response.text:
                    print(f"Response: {response.text}")
                    return True
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_audio_alternatives():
    """Test different ways to send audio."""
    print("\n2. Testing Audio Streaming Alternatives")
    print("=" * 50)
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "models/gemini-2.0-flash-live-001"
    
    # Test 1: Try with audio response modality
    print("\n🧪 Test 1: Audio response modality")
    try:
        config = {"response_modalities": ["AUDIO"]}
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected with AUDIO modality!")
            
            # Send text, expect audio back
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Say hello"}]},
                turn_complete=True
            )
            
            # Check for audio response
            import time
            start = time.time()
            async for response in session.receive():
                if response.data:
                    print(f"✅ Got audio data: {len(response.data)} bytes")
                    break
                if time.time() - start > 3:
                    print("⏱️ Timeout")
                    break
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Try sending audio in chunks
    print("\n🧪 Test 2: Chunked audio streaming")
    try:
        config = {"response_modalities": ["TEXT"]}
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected!")
            
            # Create short silence (100ms)
            import numpy as np
            sample_rate = 16000
            chunk_duration = 0.1
            samples = int(sample_rate * chunk_duration)
            
            # Send 5 chunks of silence
            print("📤 Sending 5 chunks of audio...")
            for i in range(5):
                audio_chunk = np.zeros(samples, dtype=np.int16).tobytes()
                await session.send_realtime_input(
                    audio=types.Blob(data=audio_chunk, mime_type="audio/pcm;rate=16000")
                )
                print(f"  Chunk {i+1} sent")
                await asyncio.sleep(0.1)
            
            # End stream
            print("📤 Sending audio_stream_end...")
            await session.send_realtime_input(audio_stream_end=True)
            
            # Wait for any response
            print("⏳ Waiting for response...")
            import time
            start = time.time()
            async for response in session.receive():
                if response.text is not None:
                    print(f"📥 Response: {response.text}")
                    break
                if time.time() - start > 5:
                    print("⏱️ No response after 5 seconds")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_native_audio_model():
    """Test with native audio model."""
    print("\n3. Testing Native Audio Model")
    print("=" * 50)
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Try the native audio model
    models_to_try = [
        "models/gemini-2.5-flash-preview-native-audio-dialog",
        "models/gemini-2.5-flash-exp-native-audio-thinking-dialog"
    ]
    
    for model in models_to_try:
        print(f"\n🧪 Trying: {model}")
        try:
            config = {"response_modalities": ["AUDIO"]}
            async with client.aio.live.connect(model=model, config=config) as session:
                print("✅ Connected to native audio model!")
                
                # Send text
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": "Hello, can you hear me?"}]},
                    turn_complete=True
                )
                
                # Wait for audio response
                import time
                start = time.time()
                async for response in session.receive():
                    if response.data:
                        print(f"✅ Got audio response: {len(response.data)} bytes")
                        break
                    if response.text:
                        print(f"📝 Got text: {response.text}")
                    if time.time() - start > 5:
                        print("⏱️ Timeout")
                        break
                        
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}...")


if __name__ == "__main__":
    print("🔍 MINIMAL AUDIO STREAMING TEST\n")
    print("This test isolates the audio streaming issue.\n")
    
    # Run tests
    asyncio.run(test_text_only())
    asyncio.run(test_audio_alternatives())
    asyncio.run(test_native_audio_model())