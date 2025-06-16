#!/usr/bin/env python3
"""
Test Voice Activity Detection (VAD) with proper streaming
"""

import asyncio
import os
from dotenv import load_dotenv
import time

load_dotenv()

from google import genai
from google.genai import types
import pyaudio


async def test_vad_streaming():
    """Test VAD with real microphone streaming."""
    print("Testing Voice Activity Detection (VAD)")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    # Configure with VAD enabled (this is default, but being explicit)
    config = {
        "response_modalities": ["TEXT"],
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,  # Enable VAD
                "start_of_speech_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
                "end_of_speech_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
                "prefix_padding_ms": 500,  # Include 500ms before speech starts
                "silence_duration_ms": 1000,  # 1 second of silence ends turn
            }
        }
    }
    
    pya = pyaudio.PyAudio()
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected with VAD enabled!")
            
            # Open microphone
            CHUNK_SIZE = 512  # Smaller chunks for lower latency
            RATE = 16000
            
            stream = pya.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            print("\n🎤 VAD is active. Speak naturally and pause when done.")
            print("The model will respond after detecting end of speech.")
            print("Say something like: 'Hello Gemini, what is two plus two?'")
            print("\nListening... (Press Ctrl+C to stop)\n")
            
            # Create tasks for streaming and receiving
            async def stream_audio():
                """Continuously stream audio to Gemini."""
                try:
                    while True:
                        # Read audio chunk
                        audio_chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                        
                        # Send using send_realtime_input for VAD
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=audio_chunk,
                                mime_type=f"audio/pcm;rate={RATE}"
                            )
                        )
                        
                        # No delays - continuous streaming
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Streaming error: {e}")
                finally:
                    stream.stop_stream()
                    stream.close()
            
            async def receive_responses():
                """Receive responses from Gemini."""
                try:
                    async for response in session.receive():
                        # Check for interruption
                        if hasattr(response, 'server_content') and response.server_content:
                            if hasattr(response.server_content, 'interrupted') and response.server_content.interrupted:
                                print("\n⚡ VAD: Speech interrupted")
                        
                        # Handle text response
                        if response.text is not None:
                            print(f"\n🤖 Gemini: {response.text}")
                            print("\n🎤 You can speak again...")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Receive error: {e}")
            
            # Start both tasks
            stream_task = asyncio.create_task(stream_audio())
            receive_task = asyncio.create_task(receive_responses())
            
            try:
                # Wait for tasks (they'll run until cancelled)
                await asyncio.gather(stream_task, receive_task)
            except KeyboardInterrupt:
                print("\n\n✋ Stopping...")
                stream_task.cancel()
                receive_task.cancel()
                await asyncio.gather(stream_task, receive_task, return_exceptions=True)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pya.terminate()


async def test_vad_with_pauses():
    """Test VAD behavior with pauses in audio stream."""
    print("\n\nTesting VAD with Stream Pauses")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    config = {
        "response_modalities": ["TEXT"],
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,
                "silence_duration_ms": 500,  # Shorter silence for testing
            }
        }
    }
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected!")
            
            # Simulate speaking with pauses
            print("\n📤 Simulating speech with pauses...")
            
            # Mock audio data (silence)
            silence = b'\x00' * 1600  # 100ms of silence at 16kHz
            
            # Send some "speech" (non-silence)
            print("Speaking...")
            for i in range(5):
                # Send non-silent audio (random data to simulate speech)
                import random
                speech = bytes([random.randint(1, 255) for _ in range(1600)])
                await session.send_realtime_input(
                    audio=types.Blob(data=speech, mime_type="audio/pcm;rate=16000")
                )
                await asyncio.sleep(0.1)
            
            # Pause (send silence)
            print("Pausing...")
            for i in range(10):  # 1 second of silence
                await session.send_realtime_input(
                    audio=types.Blob(data=silence, mime_type="audio/pcm;rate=16000")
                )
                await asyncio.sleep(0.1)
            
            # If stream is paused for >1 second, send audio_stream_end
            print("Stream paused - sending audio_stream_end")
            await session.send_realtime_input(audio_stream_end=True)
            
            # Wait for response
            print("\n⏳ Waiting for VAD to trigger response...")
            
            timeout = 3.0
            start_time = time.time()
            
            async for response in session.receive():
                if response.text is not None:
                    print(f"\n📝 Response: {response.text}")
                    break
                
                if time.time() - start_time > timeout:
                    print("\n⏱️ No response within timeout")
                    break
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🎙️ GEMINI LIVE API - VOICE ACTIVITY DETECTION TEST\n")
    print("This test demonstrates proper VAD usage with continuous streaming.")
    print("VAD will automatically detect when you stop speaking and trigger a response.\n")
    
    asyncio.run(test_vad_streaming())
    # asyncio.run(test_vad_with_pauses())