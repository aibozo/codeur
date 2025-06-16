#!/usr/bin/env python3
"""
Debug VAD and audio streaming issues
"""

import asyncio
import os
from dotenv import load_dotenv
import time
import numpy as np

load_dotenv()

from google import genai
from google.genai import types
import pyaudio


async def test_vad_with_debug():
    """Test VAD with detailed debugging."""
    print("Testing VAD with Debug Output")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    # Simple config first
    config = {
        "response_modalities": ["TEXT"]
    }
    
    pya = pyaudio.PyAudio()
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected!")
            
            # First, send a text message to verify connection works
            print("\n1️⃣ Testing text interaction first...")
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Say 'hello' if you can hear me"}]},
                turn_complete=True
            )
            
            # Wait for text response
            got_response = False
            async for response in session.receive():
                if response.text:
                    print(f"✅ Text response: {response.text}")
                    got_response = True
                    break
            
            if not got_response:
                print("❌ No text response - connection issue")
                return
            
            print("\n2️⃣ Now testing audio streaming with VAD...")
            
            # Open microphone
            CHUNK_SIZE = 512
            RATE = 16000
            
            stream = pya.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            print("\n🎤 Speak now for 3 seconds...")
            print("Say: 'What is two plus two?'")
            
            # Track what we're sending
            chunks_sent = 0
            total_bytes = 0
            audio_levels = []
            
            start_time = time.time()
            
            # Stream for 3 seconds
            while time.time() - start_time < 3.0:
                # Read chunk
                audio_chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                
                # Calculate audio level
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                level = np.abs(audio_array).mean()
                audio_levels.append(level)
                
                # Send chunk
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_chunk,
                        mime_type=f"audio/pcm;rate={RATE}"
                    )
                )
                
                chunks_sent += 1
                total_bytes += len(audio_chunk)
                
                # Show progress
                if chunks_sent % 10 == 0:
                    print(f"  Sent {chunks_sent} chunks, avg level: {int(level)}")
            
            stream.stop_stream()
            stream.close()
            
            print(f"\n📊 Streaming stats:")
            print(f"  Chunks sent: {chunks_sent}")
            print(f"  Total bytes: {total_bytes}")
            print(f"  Avg audio level: {int(np.mean(audio_levels))}")
            print(f"  Max audio level: {int(np.max(audio_levels))}")
            
            if np.max(audio_levels) < 100:
                print("  ⚠️ Very low audio levels - check microphone!")
            
            # Try sending audio_stream_end to trigger processing
            print("\n3️⃣ Sending audio_stream_end signal...")
            await session.send_realtime_input(audio_stream_end=True)
            
            print("\n⏳ Waiting for response (10 seconds)...")
            
            timeout = 10.0
            start_wait = time.time()
            response_count = 0
            
            async for response in session.receive():
                response_count += 1
                
                # Debug what type of response we got
                print(f"\n  Response #{response_count}:")
                
                if hasattr(response, 'text') and response.text:
                    print(f"  ✅ Text: {response.text}")
                
                if hasattr(response, 'data') and response.data:
                    print(f"  📊 Audio data: {len(response.data)} bytes")
                
                if hasattr(response, 'server_content') and response.server_content:
                    print(f"  📋 Server content: {type(response.server_content)}")
                    
                    # Check various server content fields
                    if hasattr(response.server_content, 'interrupted'):
                        print(f"     Interrupted: {response.server_content.interrupted}")
                    
                    if hasattr(response.server_content, 'turn_complete'):
                        print(f"     Turn complete: {response.server_content.turn_complete}")
                
                # Timeout check
                if time.time() - start_wait > timeout:
                    print("\n⏱️ Timeout reached")
                    break
            
            if response_count == 0:
                print("\n❌ No responses received at all")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pya.terminate()


async def test_simple_audio_file():
    """Test with a known audio file to isolate mic issues."""
    print("\n\nTesting with Audio File")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    config = {"response_modalities": ["TEXT"]}
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected!")
            
            # Create a simple audio file saying "hello"
            # This is just a tone pattern, but should trigger VAD
            sample_rate = 16000
            duration = 2.0
            
            # Generate a simple speech-like pattern
            t = np.linspace(0, duration, int(sample_rate * duration))
            # Modulate frequency to simulate speech
            freq_modulation = 300 + 100 * np.sin(2 * np.pi * 2 * t)
            audio_signal = np.sin(2 * np.pi * freq_modulation * t)
            
            # Add envelope to make it more speech-like
            envelope = np.exp(-t) * (1 - np.exp(-t * 10))
            audio_signal *= envelope
            
            # Convert to 16-bit PCM
            audio_data = (audio_signal * 16384).astype(np.int16).tobytes()
            
            print(f"\n📤 Sending {len(audio_data)} bytes of test audio...")
            
            # Send as one blob
            await session.send_realtime_input(
                audio=types.Blob(
                    data=audio_data,
                    mime_type=f"audio/pcm;rate={sample_rate}"
                )
            )
            
            # Send stream end
            await session.send_realtime_input(audio_stream_end=True)
            
            print("⏳ Waiting for response...")
            
            timeout = 5.0
            start_time = time.time()
            
            async for response in session.receive():
                if response.text:
                    print(f"✅ Response: {response.text}")
                    break
                
                if time.time() - start_time > timeout:
                    print("⏱️ Timeout")
                    break
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🔍 GEMINI LIVE API - VAD DEBUG TEST\n")
    
    # Run both tests
    asyncio.run(test_vad_with_debug())
    asyncio.run(test_simple_audio_file())