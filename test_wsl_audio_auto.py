#!/usr/bin/env python3
"""
Automated WSL audio test - no user input required.
"""

import os
import sys
import time
import numpy as np
import pyaudio
import asyncio
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


def test_audio_system():
    """Test audio system configuration."""
    print("🎵 WSL AUDIO SYSTEM TEST")
    print("=" * 50)
    
    # Check environment
    print("\n1. Environment:")
    print(f"   PULSE_SERVER: {os.environ.get('PULSE_SERVER', 'not set')}")
    
    # Set if needed
    if not os.environ.get("PULSE_SERVER") and os.path.exists("/mnt/wslg/PulseServer"):
        os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"
        print(f"   ✅ Set PULSE_SERVER to {os.environ['PULSE_SERVER']}")
    
    # Check PyAudio
    print("\n2. PyAudio Status:")
    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"   ✅ PyAudio initialized")
        print(f"   ✅ Found {device_count} audio devices")
        
        # Get default devices
        try:
            default_out = p.get_default_output_device_info()
            print(f"   ✅ Default output: {default_out['name']}")
            output_available = True
        except:
            print(f"   ❌ No default output device")
            output_available = False
        
        try:
            default_in = p.get_default_input_device_info()
            print(f"   ✅ Default input: {default_in['name']}")
            input_available = True
        except:
            print(f"   ❌ No default input device")
            input_available = False
        
        p.terminate()
        
        return output_available, input_available
        
    except Exception as e:
        print(f"   ❌ PyAudio error: {e}")
        return False, False


def test_simple_playback():
    """Test simple audio playback."""
    print("\n3. Testing Audio Playback:")
    
    p = pyaudio.PyAudio()
    
    try:
        # Generate a short beep
        duration = 0.5
        sample_rate = 44100
        frequency = 880  # A5
        
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples)
        audio = np.sin(2 * np.pi * frequency * t) * 0.5
        
        # Add fade in/out
        fade_samples = int(0.05 * sample_rate)
        audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
        audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        audio_bytes = (audio * 32767).astype(np.int16).tobytes()
        
        # Play
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True
        )
        
        print("   🔊 Playing test tone...")
        stream.write(audio_bytes)
        stream.stop_stream()
        stream.close()
        
        print("   ✅ Playback successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Playback failed: {e}")
        return False
    finally:
        p.terminate()


def test_recording():
    """Test audio recording."""
    print("\n4. Testing Audio Recording:")
    
    p = pyaudio.PyAudio()
    
    try:
        # Record 1 second
        chunk_size = 1024
        sample_rate = 16000
        duration = 1.0
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk_size
        )
        
        print("   🎤 Recording 1 second of audio...")
        frames = []
        max_level = 0
        
        for _ in range(int(sample_rate / chunk_size * duration)):
            data = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(data)
            
            # Check level
            audio_array = np.frombuffer(data, dtype=np.int16)
            level = np.max(np.abs(audio_array))
            max_level = max(max_level, level)
        
        stream.stop_stream()
        stream.close()
        
        print(f"   ✅ Recording successful")
        print(f"   📊 Max audio level: {max_level}")
        
        if max_level < 50:
            print("   ⚠️  Very quiet - microphone may not be working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Recording failed: {e}")
        return False
    finally:
        p.terminate()


async def test_gemini_audio():
    """Test Gemini audio generation."""
    print("\n5. Testing Gemini Audio:")
    
    from google import genai
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("   ❌ GEMINI_API_KEY not set")
        return False
    
    client = genai.Client(api_key=api_key)
    
    try:
        model = "models/gemini-2.0-flash-live-001"
        config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": "Zephyr"}
                }
            }
        }
        
        async with client.aio.live.connect(model=model, config=config) as session:
            print("   ✅ Connected to Gemini")
            
            # Request audio
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Say 'Audio test successful'"}]},
                turn_complete=True
            )
            
            # Wait for response
            async for response in session.receive():
                if response.data:
                    print(f"   ✅ Received {len(response.data)} bytes of audio")
                    
                    # Try to play
                    p = pyaudio.PyAudio()
                    try:
                        stream = p.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=24000,
                            output=True
                        )
                        
                        print("   🔊 Playing Gemini audio...")
                        stream.write(response.data)
                        stream.stop_stream()
                        stream.close()
                        
                        print("   ✅ Gemini audio playback successful")
                        
                    except Exception as e:
                        print(f"   ❌ Playback error: {e}")
                    finally:
                        p.terminate()
                    
                    return True
                
                if response.text:
                    print(f"   📝 Text: {response.text}")
            
            print("   ❌ No audio response")
            return False
            
    except Exception as e:
        print(f"   ❌ Gemini error: {e}")
        return False


def main():
    """Run all tests."""
    # Test basic system
    output_ok, input_ok = test_audio_system()
    
    # Test playback if available
    if output_ok:
        test_simple_playback()
    
    # Test recording if available
    if input_ok:
        test_recording()
    
    # Test Gemini
    asyncio.run(test_gemini_audio())
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    
    if output_ok and input_ok:
        print("✅ Audio system is functional")
        print("\nTo use voice agent:")
        print("  agent voice")
        print("\nNote: You may hear audio through Windows if WSLg audio is working.")
        print("The ALSA warnings can be ignored - audio routes through PulseAudio.")
    else:
        print("⚠️  Audio system has issues")
        print("\nSuggestions:")
        print("1. Make sure WSL is updated: wsl.exe --update")
        print("2. Restart WSL: wsl.exe --shutdown")
        print("3. Check Windows audio is working")
        print("4. Try: export PULSE_SERVER=unix:/mnt/wslg/PulseServer")


if __name__ == "__main__":
    main()