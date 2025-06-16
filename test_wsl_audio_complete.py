#!/usr/bin/env python3
"""
Test WSL audio setup with PyAudio and PulseAudio.
"""

import os
import sys
import time
import numpy as np
import pyaudio
from dotenv import load_dotenv

load_dotenv()

def test_pyaudio_devices():
    """List all available audio devices."""
    print("🎤 PyAudio Device Test")
    print("=" * 50)
    
    # Set PulseAudio environment if needed
    if not os.environ.get("PULSE_SERVER"):
        os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"
        print(f"Set PULSE_SERVER={os.environ['PULSE_SERVER']}")
    
    try:
        p = pyaudio.PyAudio()
        
        print(f"\nPyAudio version: {pyaudio.get_portaudio_version_text()}")
        print(f"Number of devices: {p.get_device_count()}")
        
        # List all devices
        print("\nAvailable devices:")
        print("-" * 50)
        
        default_input = None
        default_output = None
        
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(f"\nDevice {i}: {info['name']}")
            print(f"  Channels: {info['maxInputChannels']} in, {info['maxOutputChannels']} out")
            print(f"  Sample Rate: {info['defaultSampleRate']}")
            
            if info['maxInputChannels'] > 0:
                print("  ✅ Can record")
                if default_input is None:
                    default_input = i
            
            if info['maxOutputChannels'] > 0:
                print("  ✅ Can playback")
                if default_output is None:
                    default_output = i
        
        # Get default devices
        try:
            default_in = p.get_default_input_device_info()
            print(f"\n🎤 Default input device: {default_in['name']} (index {default_in['index']})")
        except:
            print("\n❌ No default input device")
        
        try:
            default_out = p.get_default_output_device_info()
            print(f"🔊 Default output device: {default_out['name']} (index {default_out['index']})")
        except:
            print("❌ No default output device")
        
        p.terminate()
        
        return default_input, default_output
        
    except Exception as e:
        print(f"\n❌ PyAudio error: {e}")
        return None, None


def test_audio_playback(device_index=None):
    """Test audio playback with a simple tone."""
    print("\n\n🔊 Audio Playback Test")
    print("=" * 50)
    
    p = pyaudio.PyAudio()
    
    # Generate a test tone
    duration = 2.0  # seconds
    sample_rate = 44100
    frequency = 440.0  # A4 note
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Create a more pleasant sound - sine wave with envelope
    envelope = np.exp(-t * 2)  # Exponential decay
    audio_data = envelope * np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM
    audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
    
    try:
        # Open stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
            output_device_index=device_index
        )
        
        print(f"Playing {frequency}Hz tone for {duration} seconds...")
        print("You should hear a sound now!")
        
        # Play audio
        stream.write(audio_bytes)
        
        # Close stream
        stream.stop_stream()
        stream.close()
        
        print("✅ Playback completed successfully")
        
    except Exception as e:
        print(f"❌ Playback error: {e}")
    finally:
        p.terminate()


def test_audio_recording(device_index=None):
    """Test audio recording."""
    print("\n\n🎤 Audio Recording Test")
    print("=" * 50)
    
    p = pyaudio.PyAudio()
    
    chunk_size = 1024
    sample_rate = 16000
    duration = 3  # seconds
    
    try:
        # Open stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=chunk_size
        )
        
        print(f"Recording for {duration} seconds...")
        print("Make some noise! (speak, clap, etc.)")
        
        frames = []
        max_level = 0
        
        for i in range(0, int(sample_rate / chunk_size * duration)):
            data = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(data)
            
            # Calculate audio level
            audio_array = np.frombuffer(data, dtype=np.int16)
            level = np.max(np.abs(audio_array))
            max_level = max(max_level, level)
            
            # Show level meter
            meter = int(level / 32768 * 50)
            print(f"\r|{'█' * meter}{' ' * (50 - meter)}| Level: {level:5d}", end='', flush=True)
        
        print("\n")
        
        # Close stream
        stream.stop_stream()
        stream.close()
        
        print(f"✅ Recording completed")
        print(f"Maximum level detected: {max_level}")
        
        if max_level < 100:
            print("⚠️  Very low audio level - microphone might not be working")
        elif max_level < 1000:
            print("⚠️  Low audio level - try speaking louder")
        else:
            print("✅ Good audio level detected")
        
        # Save recording
        if frames and max_level > 100:
            print("\nSaving recording to test_recording.raw")
            with open("test_recording.raw", "wb") as f:
                f.write(b''.join(frames))
            print("Convert with: ffmpeg -f s16le -ar 16000 -ac 1 -i test_recording.raw test_recording.wav")
        
    except Exception as e:
        print(f"\n❌ Recording error: {e}")
    finally:
        p.terminate()


def test_gemini_audio_response():
    """Test Gemini audio response playback."""
    print("\n\n🤖 Gemini Audio Response Test")
    print("=" * 50)
    
    from google import genai
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return
    
    client = genai.Client(api_key=api_key)
    
    # Test with simple model first
    print("Requesting audio from Gemini...")
    
    import asyncio
    
    async def get_audio():
        model = "models/gemini-2.0-flash-live-001"
        config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": "Zephyr"}
                }
            }
        }
        
        try:
            async with client.aio.live.connect(model=model, config=config) as session:
                # Send message
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": "Say 'Hello from Gemini' in a clear voice"}]},
                    turn_complete=True
                )
                
                # Get audio response
                async for response in session.receive():
                    if response.data:
                        print(f"✅ Received {len(response.data)} bytes of audio")
                        
                        # Try to play it
                        p = pyaudio.PyAudio()
                        try:
                            stream = p.open(
                                format=pyaudio.paInt16,
                                channels=1,
                                rate=24000,  # Gemini uses 24kHz
                                output=True
                            )
                            
                            print("Playing Gemini's response...")
                            stream.write(response.data)
                            
                            stream.stop_stream()
                            stream.close()
                            
                            print("✅ Playback successful!")
                            
                        except Exception as e:
                            print(f"❌ Playback error: {e}")
                        finally:
                            p.terminate()
                        
                        return True
                    
                    if response.text:
                        print(f"📝 Text response: {response.text}")
                
                print("❌ No audio response received")
                return False
                
        except Exception as e:
            print(f"❌ Gemini error: {e}")
            return False
    
    asyncio.run(get_audio())


def main():
    """Run all audio tests."""
    print("🎵 WSL AUDIO TEST SUITE\n")
    
    # Test 1: List devices
    input_device, output_device = test_pyaudio_devices()
    
    if output_device is not None:
        # Test 2: Playback
        response = input("\nTest audio playback? (y/n): ")
        if response.lower() == 'y':
            test_audio_playback(output_device)
    
    if input_device is not None:
        # Test 3: Recording
        response = input("\nTest audio recording? (y/n): ")
        if response.lower() == 'y':
            test_audio_recording(input_device)
    
    # Test 4: Gemini audio
    response = input("\nTest Gemini audio response? (y/n): ")
    if response.lower() == 'y':
        test_gemini_audio_response()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()