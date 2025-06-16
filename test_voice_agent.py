#!/usr/bin/env python3
"""
Comprehensive test for the voice agent with continuous audio streaming.
"""

import asyncio
import os
import sys
import time
import numpy as np
from pathlib import Path
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


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


async def test_continuous_conversation():
    """Test continuous voice conversation until interrupted."""
    print_section("Continuous Voice Conversation Test")
    
    from google import genai
    from google.genai import types
    import pyaudio
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return False
    
    client = genai.Client(api_key=api_key)
    
    # Use native audio model for better voice interaction
    model = "models/gemini-2.5-flash-preview-native-audio-dialog"
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
    
    print(f"Model: {model}")
    print("VAD Config: HIGH sensitivity, 800ms silence detection")
    print("\n🎤 Starting continuous conversation...")
    print("Speak naturally - the agent will respond when you pause.")
    print("Press Ctrl+C to stop.\n")
    
    p = pyaudio.PyAudio()
    mic_stream = None
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected to Gemini Live API")
            
            # Send initial context
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "You are a helpful voice assistant. Have a natural conversation with me. Keep responses concise and conversational."}]},
                turn_complete=True
            )
            
            # Don't wait for greeting - start streaming immediately
            
            # Open microphone for continuous streaming
            mic_stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=800  # 50ms chunks
            )
            
            print("\n🎤 Microphone active - start speaking!\n")
            
            # Create continuous tasks
            async def stream_audio_continuously():
                """Stream audio continuously until stopped."""
                try:
                    last_level_print = time.time()
                    while True:
                        audio_data = mic_stream.read(800, exception_on_overflow=False)
                        
                        # Send to Gemini
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=audio_data,
                                mime_type="audio/pcm;rate=16000"
                            )
                        )
                        
                        # Show level occasionally
                        if time.time() - last_level_print > 2.0:
                            audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            level = np.max(np.abs(audio_array))
                            if level > 1000:  # Only show when there's sound
                                meter = int(level / 32768 * 20)
                                print(f"\r🎤 |{'█' * meter}{' ' * (20 - meter)}| Level: {level:5d}", end='', flush=True)
                            last_level_print = time.time()
                        
                        await asyncio.sleep(0)
                        
                except Exception as e:
                    print(f"\n❌ Streaming error: {e}")
            
            async def receive_responses_continuously():
                """Receive and play responses continuously without blocking."""
                try:
                    response_count = 0
                    audio_queue = asyncio.Queue()
                    
                    # Audio player task
                    async def play_audio_from_queue():
                        while True:
                            audio_data = await audio_queue.get()
                            if audio_data is None:  # Shutdown signal
                                break
                            try:
                                out_stream = p.open(
                                    format=pyaudio.paInt16,
                                    channels=1,
                                    rate=24000,
                                    output=True,
                                    frames_per_buffer=2048
                                )
                                out_stream.write(audio_data)
                                out_stream.stop_stream()
                                out_stream.close()
                            except Exception as e:
                                print(f"\nAudio playback error: {e}")
                    
                    # Start audio player
                    player_task = asyncio.create_task(play_audio_from_queue())
                    
                    # Receive responses
                    async for response in session.receive():
                        if response.data:
                            response_count += 1
                            print(f"\n🔊 Response {response_count}: {len(response.data)} bytes")
                            # Queue audio for playback (non-blocking)
                            await audio_queue.put(response.data)
                        
                        # Show text if available (for debugging)
                        if response.text:
                            print(f"[Debug] Text: {response.text}")
                        
                        # Note activity
                        if hasattr(response, 'server_content') and response.server_content:
                            if hasattr(response.server_content, 'model_turn') and response.server_content.model_turn:
                                if hasattr(response.server_content.model_turn, 'parts'):
                                    print("🎙️ Agent is speaking...")
                
                except Exception as e:
                    print(f"\n❌ Receive error: {e}")
                finally:
                    await audio_queue.put(None)  # Shutdown signal
                    await player_task
            
            # Run both tasks continuously
            stream_task = asyncio.create_task(stream_audio_continuously())
            receive_task = asyncio.create_task(receive_responses_continuously())
            
            # Wait until interrupted
            try:
                await asyncio.gather(stream_task, receive_task)
            except asyncio.CancelledError:
                print("\n\n🛑 Stopping conversation...")
            
            return True
            
    except KeyboardInterrupt:
        print("\n\n👋 Conversation ended by user")
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if mic_stream:
            mic_stream.stop_stream()
            mic_stream.close()
        p.terminate()


async def test_voice_agent_integration():
    """Test the full voice agent integration."""
    print_section("Testing Voice Agent Integration")
    
    from src.voice_agent.gemini_native_audio_simple import SimplifiedNativeAudioAgent
    
    print("Creating voice agent...")
    agent = SimplifiedNativeAudioAgent(
        project_path=Path.cwd(),
        thinking_mode=False,
        voice_name="Zephyr"
    )
    
    print(f"✅ Agent created")
    print(f"📁 Project: {agent.project_path}")
    print(f"🧠 Model: {agent.model}")
    
    # Test local functions
    print("\n📊 Testing local codebase functions:")
    
    # Search test
    print("\n1. Search test:")
    result = await agent.search_codebase("voice agent")
    if result:
        print(f"✅ Found results for 'voice agent'")
    else:
        print("❌ No results found")
    
    # Architecture test
    print("\n2. Architecture test:")
    arch = await agent.get_architecture_info()
    if arch:
        print(f"✅ Got architecture info ({len(arch)} chars)")
    else:
        print("❌ No architecture info")
    
    print("\n✅ Voice agent integration test completed!")
    
    print("\n" + "=" * 60)
    print("To run the full interactive voice agent:")
    print("  ./venv/bin/python run_voice_interactive.py")
    print("Or:")
    print("  agent voice")


async def main():
    """Run continuous conversation test."""
    print("🎵 VOICE AGENT CONTINUOUS CONVERSATION TEST\n")
    print("This will run continuously until you press Ctrl+C\n")
    
    # Run the continuous conversation
    await test_continuous_conversation()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")