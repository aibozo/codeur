#!/usr/bin/env python3
"""
Test complete voice mode integration (STT + TTS).
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from src.voice_agent.tts_voice_mode import TTSVoiceMode
from src.voice_agent.stt_whisper import WhisperSTT


async def test_voice_conversation():
    """Test a complete voice conversation flow."""
    print("🎤 Voice Mode Integration Test")
    print("=" * 60)
    
    # Check API keys
    has_google = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    
    print(f"Google API Key: {'✅ Set' if has_google else '❌ Not set'}")
    print(f"OpenAI API Key: {'✅ Set' if has_openai else '❌ Not set'}")
    print()
    
    if not has_google:
        print("⚠️  GOOGLE_API_KEY required for TTS")
        print("   Set with: export GOOGLE_API_KEY='your-key'")
        return
        
    # Initialize TTS
    try:
        tts = TTSVoiceMode()
        print("✅ TTS initialized")
    except Exception as e:
        print(f"❌ TTS initialization failed: {e}")
        return
    
    # Initialize STT (if OpenAI key available)
    stt = None
    if has_openai:
        try:
            stt = WhisperSTT()
            print(f"✅ STT initialized (can record: {stt.can_record})")
        except Exception as e:
            print(f"❌ STT initialization failed: {e}")
    else:
        print("⚠️  STT not available (no OpenAI key)")
    
    print("\n" + "-" * 60)
    
    # Test TTS
    print("\n1. Testing TTS (Text-to-Speech)...")
    test_text = "Hello! I'm your AI architect. I can help you design and build software projects."
    
    audio_file = await tts.text_to_speech(test_text, play=True)
    if audio_file:
        print(f"✅ TTS successful: {audio_file}")
    else:
        print("❌ TTS failed")
    
    # Test STT (if available)
    if stt and stt.can_record:
        print("\n2. Testing STT (Speech-to-Text)...")
        print("Press Enter to start recording (speak for 5 seconds)...")
        input()
        
        text, audio_file = stt.record_and_transcribe(duration=5, keep_audio=True)
        if text:
            print(f"✅ STT successful: '{text}'")
            if audio_file:
                print(f"   Audio saved: {audio_file}")
        else:
            print("❌ STT failed")
    
    # Simulate full conversation flow
    print("\n3. Testing Full Conversation Flow...")
    print("-" * 40)
    
    # User input (simulated or from STT)
    if stt and text:
        user_input = text
        print(f"User (from STT): {user_input}")
    else:
        user_input = "Can you help me build a web application?"
        print(f"User (simulated): {user_input}")
    
    # Generate response (simulated architect response)
    architect_response = "I'd be happy to help you build a web application. Let me create a plan with frontend, backend, and database components. What specific features do you need?"
    print(f"\nArchitect: {architect_response}")
    
    # Convert response to speech
    print("\nGenerating speech response...")
    audio_file = await tts.text_to_speech(architect_response, play=True)
    if audio_file:
        print(f"✅ Response spoken successfully")
    else:
        print("❌ Failed to speak response")
    
    print("\n" + "=" * 60)
    print("Voice mode test complete!")
    
    # Summary
    print("\nSummary:")
    print(f"- TTS: {'✅ Working' if audio_file else '❌ Not working'}")
    print(f"- STT: {'✅ Working' if (stt and stt.can_record) else '⚠️  Not available'}")
    print(f"- Voice Mode: {'✅ Ready' if (has_google and audio_file) else '❌ Not ready'}")


async def test_browser_integration():
    """Test browser-based voice integration."""
    print("\n4. Browser Integration Notes")
    print("-" * 40)
    print("The frontend supports voice mode with:")
    print("- Voice Mode toggle button")
    print("- Microphone button for speech input (Chrome/Edge)")
    print("- Audio playback for TTS responses")
    print("- Visual indicators for listening/speaking")
    print("\nTo test in browser:")
    print("1. Start the backend: python minimal_webhook_server.py")
    print("2. Start the frontend: cd frontend && npm run dev")
    print("3. Enable Voice Mode in the chat interface")
    print("4. Click the microphone to speak")
    print("5. Responses will be spoken aloud")


if __name__ == "__main__":
    asyncio.run(test_voice_conversation())
    asyncio.run(test_browser_integration())