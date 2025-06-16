#!/usr/bin/env python3
"""
Simple beep test for audio playback.
Tests audio without requiring Gemini API.
"""

import os
import sys
import platform
import subprocess
import tempfile
import wave
import struct
import math


def generate_beep_wav(filename, frequency=440, duration=0.5, sample_rate=44100):
    """Generate a simple beep sound as a WAV file."""
    # Calculate number of samples
    num_samples = int(sample_rate * duration)
    
    # Generate sine wave
    samples = []
    for i in range(num_samples):
        t = float(i) / sample_rate
        value = int(32767 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', value))
    
    # Write WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return filename


def play_beep_system(filename):
    """Play beep using system audio player."""
    system = platform.system().lower()
    
    try:
        if system == "darwin":  # macOS
            subprocess.run(["afplay", filename], check=True)
            return "afplay (macOS)"
        elif system == "windows":
            import winsound
            winsound.PlaySound(filename, winsound.SND_FILENAME)
            return "winsound (Windows)"
        elif system == "linux":
            # Try different Linux audio players
            if subprocess.run(["which", "aplay"], capture_output=True).returncode == 0:
                subprocess.run(["aplay", filename], check=True)
                return "aplay (ALSA)"
            elif subprocess.run(["which", "paplay"], capture_output=True).returncode == 0:
                subprocess.run(["paplay", filename], check=True)
                return "paplay (PulseAudio)"
            elif subprocess.run(["which", "ffplay"], capture_output=True).returncode == 0:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", filename], 
                              check=True, capture_output=True)
                return "ffplay (FFmpeg)"
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"System player error: {e}")
        return None


def play_beep_python(filename):
    """Play beep using Python libraries."""
    # Try pygame
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        return "pygame"
    except ImportError:
        pass
    except Exception as e:
        print(f"pygame error: {e}")
    
    # Try pyaudio
    try:
        import pyaudio
        import wave
        
        wf = wave.open(filename, 'rb')
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()
        return "pyaudio"
    except ImportError:
        pass
    except Exception as e:
        print(f"pyaudio error: {e}")
    
    # Try playsound
    try:
        import playsound
        playsound.playsound(filename)
        return "playsound"
    except ImportError:
        pass
    except Exception as e:
        print(f"playsound error: {e}")
    
    return None


def main():
    """Run beep test."""
    print("🔊 Audio Beep Test")
    print("=" * 50)
    print(f"Platform: {platform.platform()}")
    print()
    
    # Create temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        beep_file = tmp.name
    
    try:
        # Generate beep
        print("Generating beep sound...")
        generate_beep_wav(beep_file, frequency=440, duration=0.5)
        print(f"✅ Beep file created: {beep_file}")
        print(f"   Size: {os.path.getsize(beep_file)} bytes")
        print()
        
        # Try system player first
        print("Testing system audio player...")
        player = play_beep_system(beep_file)
        if player:
            print(f"✅ Beep played successfully using: {player}")
            return
        else:
            print("❌ No system audio player worked")
            print()
        
        # Try Python libraries
        print("Testing Python audio libraries...")
        player = play_beep_python(beep_file)
        if player:
            print(f"✅ Beep played successfully using: {player}")
            return
        else:
            print("❌ No Python audio libraries worked")
            print()
        
        # No audio playback available
        print("⚠️  No audio playback method available!")
        print()
        print("To enable audio:")
        
        if platform.system() == "Linux":
            print("  Install system player:")
            print("    sudo apt-get install alsa-utils  # For aplay")
            print("    sudo apt-get install pulseaudio  # For paplay")
            print("    sudo apt-get install ffmpeg      # For ffplay")
        
        print("\n  Or install Python library:")
        print("    pip install pygame     # Recommended")
        print("    pip install pyaudio    # Alternative")
        print("    pip install playsound  # Simple option")
        
    finally:
        # Clean up
        if os.path.exists(beep_file):
            os.unlink(beep_file)
            print(f"\n🧹 Cleaned up temporary file")


if __name__ == "__main__":
    main()