#!/usr/bin/env python3
"""
Test proper audio streaming to Gemini Live API - Fixed version
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import numpy as np
import time

load_dotenv()

from google import genai
from google.genai import types
import pyaudio


async def test_continuous_streaming():
    """Test continuous audio streaming."""
    print("Testing Continuous Audio Streaming")
    print("=" * 50)
    
    # Initialize client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    # Configure for audio input with text output
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"]
    )
    
    print(f"Connecting to {MODEL}...")
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected successfully!")
            
            # Create a test message: "Hello, can you hear me?"
            # We'll create audio that says this using tone patterns
            sample_rate = 16000
            chunk_duration = 0.1  # 100ms chunks
            chunk_samples = int(sample_rate * chunk_duration)
            
            print("\n📤 Streaming audio chunks...")
            
            # First, send a greeting message for context
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "I'm going to send you some audio. Please transcribe what you hear."}]},
                turn_complete=True
            )
            
            # Wait a moment
            await asyncio.sleep(0.5)
            
            # Stream audio chunks - simulate speaking "Hello"
            # We'll use different frequencies to simulate speech patterns
            frequencies = [300, 400, 350, 500, 400]  # Rough speech-like pattern
            
            for i, freq in enumerate(frequencies):
                # Generate chunk
                t = np.linspace(0, chunk_duration, chunk_samples)
                # Add some noise to make it more speech-like
                audio_signal = np.sin(2 * np.pi * freq * t) * 0.5
                audio_signal += np.random.normal(0, 0.1, chunk_samples)
                
                # Convert to 16-bit PCM
                audio_chunk = (audio_signal * 16384).astype(np.int16).tobytes()
                
                # Send chunk
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_chunk,
                        mime_type=f"audio/pcm;rate={sample_rate}"
                    )
                )
                
                print(f"  Sent chunk {i+1}/{len(frequencies)} ({len(audio_chunk)} bytes)")
                
                # Small delay between chunks to simulate natural speech
                await asyncio.sleep(0.05)
            
            # Don't send audio_stream_end - let VAD handle it
            print("\n⏳ Waiting for VAD to detect end of speech...")
            
            # Set a timeout for receiving response
            timeout = 5.0
            start_time = time.time()
            response_received = False
            
            async for response in session.receive():
                if response.text is not None:
                    print(f"\n📝 Response: {response.text}")
                    response_received = True
                    break
                
                if time.time() - start_time > timeout:
                    print("\n⏱️ Timeout waiting for response")
                    break
            
            if response_received:
                print("\n✅ Streaming works!")
            else:
                print("\n❓ No response received")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_real_mic_streaming():
    """Test real microphone streaming with proper chunking."""
    print("\n\nTesting Real Microphone Streaming")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        # Let VAD handle speech detection
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                silence_duration_ms=1000  # 1 second of silence ends speech
            )
        )
    )
    
    pya = pyaudio.PyAudio()
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected!")
            
            # Send initial prompt
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "I'm going to speak to you. Please respond to what I say."}]},
                turn_complete=True
            )
            
            # Open microphone
            CHUNK_SIZE = 1024  # Smaller chunks for real-time
            stream = pya.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            print("\n🎤 Speak now! (5 seconds)...")
            print("Say something like: 'Hello Gemini, how are you today?'")
            
            # Create a task to stream audio
            async def stream_audio():
                start_time = time.time()
                chunks_sent = 0
                
                while time.time() - start_time < 5.0:
                    try:
                        # Read audio chunk
                        audio_chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                        
                        # Send chunk immediately
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=audio_chunk,
                                mime_type="audio/pcm;rate=16000"
                            )
                        )
                        chunks_sent += 1
                        
                        # No delay - stream continuously
                    except Exception as e:
                        print(f"Error: {e}")
                        break
                
                stream.stop_stream()
                stream.close()
                print(f"\n📤 Streamed {chunks_sent} chunks")
            
            # Start audio streaming task
            audio_task = asyncio.create_task(stream_audio())
            
            # Listen for responses concurrently
            print("⏳ Listening for responses...")
            
            async for response in session.receive():
                if response.text:
                    print(f"\n📝 Response: {response.text}")
                    # Continue listening for more responses
                
                # Check if audio task is done
                if audio_task.done():
                    await asyncio.sleep(2)  # Wait a bit more for final responses
                    break
            
            # Ensure audio task completes
            await audio_task
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pya.terminate()


if __name__ == "__main__":
    asyncio.run(test_continuous_streaming())
    asyncio.run(test_real_mic_streaming())