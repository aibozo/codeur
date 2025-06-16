#!/usr/bin/env python3
"""
Check available voice activation features.
"""

import sys
import platform


def check_feature(name, import_test):
    """Check if a feature is available."""
    try:
        import_test()
        print(f"✅ {name}")
        return True
    except ImportError as e:
        print(f"❌ {name} - {str(e).split('No module named')[1] if 'No module' in str(e) else 'not installed'}")
        return False
    except Exception as e:
        print(f"⚠️  {name} - {e}")
        return False


print("🎤 Voice Mode Feature Check")
print("=" * 50)
print(f"Platform: {platform.system()} {platform.release()}")
print()

print("Core Requirements:")
tts = check_feature("TTS (google-genai)", lambda: __import__('google.genai'))
stt = check_feature("STT (openai)", lambda: __import__('openai'))

print("\nEnhanced Features:")
keyboard = check_feature("Push-to-Talk (keyboard)", lambda: __import__('keyboard'))
pyaudio = check_feature("Audio Input (pyaudio)", lambda: __import__('pyaudio'))
numpy = check_feature("Voice Detection (numpy)", lambda: __import__('numpy'))
pygame = check_feature("Audio Playback (pygame)", lambda: __import__('pygame'))

print("\nRecommended Setup:")
if not keyboard:
    print("📌 For Push-to-Talk: pip install keyboard")
    if platform.system() == "Linux":
        print("   Note: May require sudo on Linux")
        
if not pyaudio:
    print("📌 For Voice Activity Detection: pip install pyaudio")
    if platform.system() == "Darwin":
        print("   On macOS: brew install portaudio && pip install pyaudio")
    elif platform.system() == "Linux":
        print("   On Linux: sudo apt-get install portaudio19-dev && pip install pyaudio")
        
if not numpy:
    print("📌 For Voice Detection: pip install numpy")

if not pygame:
    print("📌 For Better Audio: pip install pygame")

print("\nAvailable Modes:")
if keyboard:
    print("✅ Push-to-Talk Mode (recommended)")
if pyaudio and numpy:
    print("✅ Voice Activity Detection Mode")
print("✅ Timeout Mode (always available)")

# Check environment variables
print("\nAPI Keys:")
import os
from dotenv import load_dotenv
load_dotenv()

if os.environ.get("GOOGLE_API_KEY"):
    print("✅ GOOGLE_API_KEY set (TTS ready)")
else:
    print("❌ GOOGLE_API_KEY not set")
    
if os.environ.get("OPENAI_API_KEY"):
    print("✅ OPENAI_API_KEY set (STT ready)")
else:
    print("❌ OPENAI_API_KEY not set")