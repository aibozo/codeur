#!/usr/bin/env python3
"""
Test audio playback support on the current system.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_system_audio():
    """Check system audio player availability."""
    system = platform.system()
    print(f"Operating System: {system}")
    print(f"Platform: {platform.platform()}")
    print("-" * 50)
    
    audio_available = False
    
    if system == "Darwin":  # macOS
        print("Checking macOS audio support...")
        if subprocess.run(["which", "afplay"], capture_output=True).returncode == 0:
            print("✅ afplay found - audio playback supported")
            audio_available = True
        else:
            print("❌ afplay not found - unusual for macOS")
            
    elif system == "Windows":
        print("Checking Windows audio support...")
        try:
            import winsound
            print("✅ winsound module available - audio playback supported")
            audio_available = True
        except ImportError:
            print("❌ winsound module not available")
            
    elif system == "Linux":
        print("Checking Linux audio players...")
        players = {
            "aplay": "ALSA sound player",
            "paplay": "PulseAudio player",
            "ffplay": "FFmpeg player"
        }
        
        for player, description in players.items():
            result = subprocess.run(["which", player], capture_output=True)
            if result.returncode == 0:
                print(f"✅ {player} found ({description})")
                audio_available = True
            else:
                print(f"❌ {player} not found")
                
    else:
        print(f"⚠️  Unknown operating system: {system}")
    
    return audio_available


def check_python_audio():
    """Check Python audio library availability."""
    print("\nChecking Python audio libraries...")
    print("-" * 50)
    
    libraries = {
        "pygame": "Cross-platform game/multimedia library",
        "pyaudio": "Python bindings for PortAudio",
        "sounddevice": "Play and record sound",
        "playsound": "Simple cross-platform audio player"
    }
    
    available = []
    
    for lib, description in libraries.items():
        try:
            __import__(lib)
            print(f"✅ {lib} available - {description}")
            available.append(lib)
        except ImportError:
            print(f"❌ {lib} not installed")
    
    return available


def test_tts_module():
    """Test if TTS module can be initialized."""
    print("\nTesting TTS Voice Mode module...")
    print("-" * 50)
    
    try:
        from src.voice_agent.tts_voice_mode import TTSVoiceMode
        print("✅ TTS module imported successfully")
        
        # Check for API key
        if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
            print("✅ GOOGLE_API_KEY is set")
            try:
                tts = TTSVoiceMode()
                print(f"✅ TTS initialized successfully")
                print(f"   Voice: {tts.voice_name}")
                print(f"   Model: {tts.tts_model}")
                print(f"   Playback supported: {tts.playback_supported}")
                return True
            except Exception as e:
                print(f"❌ TTS initialization failed: {e}")
                return False
        else:
            print("❌ GOOGLE_API_KEY not set")
            print("   Set it with: export GOOGLE_API_KEY='your-key'")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import TTS module: {e}")
        return False


def main():
    """Run all audio support tests."""
    print("Audio Support Test")
    print("=" * 60)
    
    # Check system audio
    system_audio = check_system_audio()
    
    # Check Python libraries
    python_audio = check_python_audio()
    
    # Test TTS module
    tts_ready = test_tts_module()
    
    # Summary
    print("\nSummary")
    print("=" * 60)
    
    if system_audio or python_audio:
        print("✅ Audio playback is supported on this system")
        if system_audio:
            print("   - System audio player available")
        if python_audio:
            print(f"   - Python libraries available: {', '.join(python_audio)}")
    else:
        print("⚠️  No audio playback support detected")
        print("\nTo enable audio playback:")
        if platform.system() == "Linux":
            print("   - Install ALSA: sudo apt-get install alsa-utils")
            print("   - Or install FFmpeg: sudo apt-get install ffmpeg")
        print("   - Or install pygame: pip install pygame")
    
    if tts_ready:
        print("\n✅ TTS Voice Mode is ready to use")
    else:
        print("\n❌ TTS Voice Mode is not ready")
        if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
            print("   - Set GOOGLE_API_KEY environment variable")
    
    print("\nFor detailed setup instructions, see: docs/VOICE_MODE_SETUP.md")


if __name__ == "__main__":
    main()