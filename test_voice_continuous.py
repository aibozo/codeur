#!/usr/bin/env python3
"""
Simple continuous voice streaming test with correct audio specs.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Suppress ALSA errors
from ctypes import *
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# Set environment
if not os.environ.get("PULSE_SERVER"):
    os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"


async def main():
    """Run continuous voice streaming."""
    print("🎤 CONTINUOUS VOICE STREAMING TEST")
    print("=" * 50)
    print("Audio specs:")
    print("- Input: 16-bit PCM, 16kHz mono")
    print("- Output: 24kHz")
    print("\nPress Ctrl+C to stop\n")
    
    from google import genai
    from google.genai import types
    import pyaudio
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return
    
    client = genai.Client(api_key=api_key)
    
    # Config with explicit VAD settings
    model = "models/gemini-2.0-flash-live-001"
    config = {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {"voice_name": "Zephyr"}
            }
        },
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,
                "start_of_speech_sensitivity": types.StartSensitivity.START_SENSITIVITY_HIGH,
                "end_of_speech_sensitivity": types.EndSensitivity.END_SENSITIVITY_HIGH,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 800
            }
        }
    }
    
    p = pyaudio.PyAudio()
    
    try:
        # Open microphone - 16kHz mono input
        mic_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=800  # 50ms chunks
        )
        
        # Open speaker - 24kHz output
        speaker_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=1200  # Adjusted for 24kHz
        )
        
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected to Gemini Live API")
            print("🎤 Start speaking!\n")
            
            # Send initial greeting to trigger a response
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Hello, I'm testing audio. Please greet me briefly."}]},
                turn_complete=True
            )
            
            # Simple continuous streaming
            async def stream_mic():
                """Stream microphone to Gemini."""
                import numpy as np
                import time
                
                chunk_count = 0
                last_log = time.time()
                
                while True:
                    try:
                        # Read from mic (16kHz)
                        audio_data = mic_stream.read(800, exception_on_overflow=False)
                        
                        # Send to Gemini
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=audio_data,
                                mime_type="audio/pcm;rate=16000"
                            )
                        )
                        
                        chunk_count += 1
                        
                        # Log every 2 seconds
                        if time.time() - last_log > 2.0:
                            # Check audio level
                            audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            level = np.max(np.abs(audio_array))
                            print(f"📊 Sent {chunk_count} chunks, Level: {level}")
                            last_log = time.time()
                        
                        await asyncio.sleep(0)  # Yield
                        
                    except Exception as e:
                        print(f"Stream error: {e}")
                        break
            
            async def play_responses():
                """Play responses from Gemini."""
                count = 0
                async for response in session.receive():
                    try:
                        if response.data:
                            count += 1
                            print(f"🔊 Response {count}: {len(response.data)} bytes ", end='', flush=True)
                            
                            # Play at 24kHz
                            speaker_stream.write(response.data)
                            print("✓")
                            
                    except Exception as e:
                        print(f"\nPlayback error: {e}")
            
            # Run both concurrently
            await asyncio.gather(
                stream_mic(),
                play_responses()
            )
            
    except KeyboardInterrupt:
        print("\n\n✅ Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()
        p.terminate()


if __name__ == "__main__":
    asyncio.run(main())