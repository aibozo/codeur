#!/usr/bin/env python3
"""
Test microphone recording in WSL
"""

import pyaudio
import wave
import numpy as np
import time
import sys

def list_audio_devices():
    """List all audio devices with details."""
    p = pyaudio.PyAudio()
    
    print("\n🎤 AUDIO DEVICES:")
    print("=" * 60)
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"\nDevice {i}: {info['name']}")
        print(f"  Host API: {p.get_host_api_info_by_index(info['hostApi'])['name']}")
        print(f"  Max input channels: {info['maxInputChannels']}")
        print(f"  Max output channels: {info['maxOutputChannels']}")
        print(f"  Default sample rate: {info['defaultSampleRate']}")
        
    p.terminate()

def test_microphone(device_index=None, duration=3):
    """Test microphone recording."""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
    p = pyaudio.PyAudio()
    
    try:
        # Get device info
        if device_index is not None:
            device_info = p.get_device_info_by_index(device_index)
            print(f"\n🎤 Testing device {device_index}: {device_info['name']}")
        else:
            device_info = p.get_default_input_device_info()
            print(f"\n🎤 Testing default input device: {device_info['name']}")
            device_index = device_info['index']
        
        # Open stream
        print(f"Opening audio stream (channels={CHANNELS}, rate={RATE})...")
        
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
        
        print(f"✅ Stream opened successfully!")
        print(f"📍 Recording for {duration} seconds... Speak into your microphone!")
        print("   Level meter:")
        
        frames = []
        start_time = time.time()
        
        # Record and show audio levels
        while time.time() - start_time < duration:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # Calculate and display audio level
                audio_data = np.frombuffer(data, dtype=np.int16)
                level = np.abs(audio_data).mean()
                max_level = 32768  # Max for int16
                normalized_level = int((level / max_level) * 50)
                
                # Display level meter
                bar = "█" * normalized_level + "░" * (50 - normalized_level)
                sys.stdout.write(f"\r   [{bar}] {level:.0f}")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"\n❌ Error reading audio: {e}")
                break
        
        print("\n✅ Recording complete!")
        
        # Close stream
        stream.stop_stream()
        stream.close()
        
        # Save recording
        filename = f"test_recording_{device_index}.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"💾 Saved recording to: {filename}")
        
        # Analyze recording
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        avg_level = np.abs(audio_data).mean()
        max_amplitude = np.abs(audio_data).max()
        
        print(f"\n📊 Recording analysis:")
        print(f"   Average level: {avg_level:.0f}")
        print(f"   Max amplitude: {max_amplitude}")
        print(f"   Silence threshold: ~100")
        
        if avg_level < 100:
            print("   ⚠️  Recording appears to be silent or very quiet!")
            print("   Check your microphone settings or permissions.")
        else:
            print("   ✅ Audio detected in recording!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        p.terminate()

def test_pulseaudio_sources():
    """Test PulseAudio sources."""
    import subprocess
    
    print("\n🔊 PULSEAUDIO SOURCE DETAILS:")
    print("=" * 60)
    
    # Get detailed source info
    result = subprocess.run(["pactl", "list", "sources"], capture_output=True, text=True)
    if result.returncode == 0:
        lines = result.stdout.split('\n')
        in_source = False
        for line in lines:
            if line.startswith("Source #"):
                in_source = True
                print(f"\n{line}")
            elif in_source and line.strip() == "":
                in_source = False
            elif in_source and any(key in line for key in ["Name:", "Description:", "State:", "Volume:"]):
                print(f"  {line.strip()}")

def suggest_mic_fixes():
    """Suggest fixes for microphone issues."""
    print("\n💡 MICROPHONE TROUBLESHOOTING:")
    print("=" * 60)
    print("""
1. **Check Windows audio settings:**
   - Right-click speaker icon > Sound settings
   - Ensure your headset is the default recording device
   - Check microphone privacy settings

2. **For USB headsets in WSL:**
   - Install usbipd-win on Windows: winget install usbipd
   - List USB devices: usbipd list
   - Attach headset: usbipd attach --wsl --busid <BUSID>

3. **Test with different audio sources:**
   - Try: pactl set-default-source RDPSource
   - Or create a loopback: pactl load-module module-loopback

4. **Alternative: Use Windows audio passthrough:**
   - Install VB-Audio Virtual Cable on Windows
   - Route audio through virtual cable
   - Access in WSL via RDP audio

5. **Debug PulseAudio:**
   - Check logs: journalctl -u pulseaudio
   - Verbose mode: pulseaudio -vvv
   - Monitor sources: pactl subscribe
""")

def main():
    """Run microphone tests."""
    print("🎤 WSL MICROPHONE TEST")
    print("=" * 60)
    
    # List devices
    list_audio_devices()
    
    # Test PulseAudio sources
    test_pulseaudio_sources()
    
    # Test default microphone
    print("\n" + "="*60)
    print("TESTING DEFAULT MICROPHONE")
    print("="*60)
    test_microphone(duration=3)
    
    # Suggest fixes
    suggest_mic_fixes()
    
    print("\n✅ Tests complete!")
    print("\nTo play back recordings:")
    print("  python -c \"import pyaudio, wave; ...")
    print("  Or: aplay test_recording_*.wav")

if __name__ == "__main__":
    main()