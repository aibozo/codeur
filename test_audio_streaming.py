#!/usr/bin/env python3
"""
Test proper audio streaming to Gemini Live API
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types
import pyaudio
import numpy as np


async def test_audio_streaming():
    """Test audio streaming with the correct format."""
    print("Testing Audio Streaming to Gemini Live API")
    print("=" * 50)
    
    # Initialize client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    # Configure for audio-to-text to test
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],  # Get text response to verify
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False
            )
        )
    )
    
    print(f"Connecting to {MODEL}...")
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected successfully!")
            
            # Create a test audio signal (sine wave)
            sample_rate = 16000
            duration = 2  # seconds
            frequency = 440  # A4 note
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_signal = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            audio_data = (audio_signal * 32767).astype(np.int16).tobytes()
            
            print(f"\n📤 Sending {len(audio_data)} bytes of test audio (2 sec sine wave)...")
            
            # Send audio using the correct method from documentation
            await session.send_realtime_input(
                audio=types.Blob(
                    data=audio_data,
                    mime_type=f"audio/pcm;rate={sample_rate}"
                )
            )
            
            # Signal end of audio stream
            await session.send_realtime_input(audio_stream_end=True)
            
            print("⏳ Waiting for response...")
            
            # Receive response
            response_received = False
            async for response in session.receive():
                if response.text is not None:
                    print(f"📝 Response: {response.text}")
                    response_received = True
                    break
            
            if response_received:
                print("\n✅ Audio streaming works!")
            else:
                print("\n❌ No response received")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_mic_streaming():
    """Test microphone streaming."""
    print("\n\nTesting Microphone Streaming")
    print("=" * 50)
    
    # Initialize
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"]
    )
    
    pya = pyaudio.PyAudio()
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected!")
            
            # Open microphone
            stream = pya.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            print("\n🎤 Recording for 3 seconds... Speak now!")
            
            # Record and send chunks
            start_time = asyncio.get_event_loop().time()
            chunks_sent = 0
            
            while asyncio.get_event_loop().time() - start_time < 3:
                audio_chunk = stream.read(1024, exception_on_overflow=False)
                
                # Send chunk
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_chunk,
                        mime_type="audio/pcm;rate=16000"
                    )
                )
                chunks_sent += 1
            
            stream.stop_stream()
            stream.close()
            
            # Signal end of audio stream
            await session.send_realtime_input(audio_stream_end=True)
            
            print(f"📤 Sent {chunks_sent} audio chunks")
            print("⏳ Waiting for response...")
            
            # Get response
            async for response in session.receive():
                if response.text:
                    print(f"📝 Transcript: {response.text}")
                    break
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        pya.terminate()


if __name__ == "__main__":
    asyncio.run(test_audio_streaming())
    asyncio.run(test_mic_streaming())