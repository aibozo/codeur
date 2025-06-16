#!/usr/bin/env python3
"""
Test audio format exactly as shown in documentation
"""

import asyncio
import os
from dotenv import load_dotenv
import io
import numpy as np

load_dotenv()

from google import genai
from google.genai import types
import pyaudio

# Try to import audio libraries
try:
    import soundfile as sf
    import librosa
    AUDIO_LIBS = True
except ImportError:
    AUDIO_LIBS = False
    print("Warning: soundfile/librosa not installed. Install with: pip install soundfile librosa")


async def test_documented_format():
    """Test using the exact format from documentation."""
    print("Testing Documented Audio Format")
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
            
            # Create audio exactly as shown in docs
            sample_rate = 16000
            duration = 2.0
            
            # Generate a simple "hello" pattern
            # We'll use frequency modulation to simulate speech
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # Create segments for "hel-lo"
            segment1 = np.sin(2 * np.pi * 300 * t[:len(t)//2])  # "hel"
            segment2 = np.sin(2 * np.pi * 400 * t[len(t)//2:])  # "lo"
            
            audio_signal = np.concatenate([segment1, segment2])
            
            # Apply envelope
            envelope = np.ones_like(audio_signal)
            envelope[:1000] = np.linspace(0, 1, 1000)  # Attack
            envelope[-1000:] = np.linspace(1, 0, 1000)  # Release
            audio_signal *= envelope * 0.8
            
            # Convert to 16-bit PCM as in docs
            audio_16bit = (audio_signal * 32767).astype(np.int16)
            
            if AUDIO_LIBS:
                # Use the exact method from documentation
                buffer = io.BytesIO()
                sf.write(buffer, audio_16bit, sample_rate, format='RAW', subtype='PCM_16')
                buffer.seek(0)
                audio_bytes = buffer.read()
            else:
                # Direct conversion
                audio_bytes = audio_16bit.tobytes()
            
            print(f"\n📤 Sending {len(audio_bytes)} bytes using documented format...")
            
            # Send exactly as shown in documentation
            await session.send_realtime_input(
                audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
            )
            
            # Don't send audio_stream_end - let VAD handle it as docs suggest
            
            print("⏳ Waiting for VAD to process...")
            
            # Listen for response
            timeout = 10.0
            import time
            start_time = time.time()
            
            async for response in session.receive():
                if response.text is not None:
                    print(f"\n✅ Transcription: {response.text}")
                    break
                
                # Debug other response types
                if hasattr(response, 'server_content') and response.server_content:
                    if hasattr(response.server_content, 'model_turn'):
                        print("📝 Model turn received")
                
                if time.time() - start_time > timeout:
                    print("\n⏱️ Timeout - no transcription received")
                    break
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_microphone_with_proper_format():
    """Test microphone with proper audio format."""
    print("\n\nTesting Microphone with Proper Format")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    MODEL = "models/gemini-2.0-flash-live-001"
    
    # Enable input transcription to see what Gemini hears
    config = {
        "response_modalities": ["TEXT"],
        "input_audio_transcription": {},  # Enable input transcription
    }
    
    pya = pyaudio.PyAudio()
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Connected with input transcription enabled!")
            
            # First send a context message
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "I'm going to speak. Please transcribe what I say and then answer any questions."}]},
                turn_complete=True
            )
            
            # Wait for acknowledgment
            async for response in session.receive():
                if response.text:
                    print(f"Model: {response.text}")
                    break
            
            # Now start audio
            CHUNK_SIZE = 1024  # Larger chunk for better quality
            RATE = 16000
            
            stream = pya.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            print("\n🎤 Speak clearly for 4 seconds...")
            print("Try saying: 'Hello Gemini, what is two plus two?'")
            print("\nListening...")
            
            import time
            start_time = time.time()
            chunks_sent = 0
            
            # Record and stream
            while time.time() - start_time < 4.0:
                try:
                    # Read chunk
                    audio_chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    
                    # Send immediately
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_chunk,
                            mime_type="audio/pcm;rate=16000"
                        )
                    )
                    
                    chunks_sent += 1
                    
                except Exception as e:
                    print(f"Error: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            
            print(f"\n📤 Sent {chunks_sent} chunks")
            print("⏳ Waiting for transcription and response...")
            
            # Listen for responses
            transcription_received = False
            response_received = False
            
            timeout = 10.0
            start_wait = time.time()
            
            async for msg in session.receive():
                # Check for input transcription
                if hasattr(msg, 'server_content') and msg.server_content:
                    if hasattr(msg.server_content, 'input_transcription') and msg.server_content.input_transcription:
                        print(f"\n📝 What I heard: '{msg.server_content.input_transcription.text}'")
                        transcription_received = True
                
                # Check for response
                if msg.text:
                    print(f"\n🤖 Response: {msg.text}")
                    response_received = True
                
                # Exit if we got both
                if transcription_received and response_received:
                    print("\n✅ Success! Audio was transcribed and processed.")
                    break
                
                if time.time() - start_wait > timeout:
                    print("\n⏱️ Timeout")
                    if not transcription_received:
                        print("❌ No input transcription received - audio may not be reaching Gemini")
                    if not response_received:
                        print("❌ No response received")
                    break
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pya.terminate()


if __name__ == "__main__":
    print("🎵 GEMINI LIVE API - AUDIO FORMAT TEST\n")
    
    asyncio.run(test_documented_format())
    asyncio.run(test_microphone_with_proper_format())