#!/usr/bin/env python3
"""
Simple test of TTS functionality.
"""

import asyncio
from dotenv import load_dotenv
from src.voice_agent.tts_voice_mode import TTSVoiceMode

# Load environment variables
load_dotenv()

async def main():
    print("🎤 Testing TTS Voice Output")
    print("=" * 50)
    
    # Create TTS
    tts = TTSVoiceMode(voice_name="Kore")
    
    # Test different messages
    messages = [
        "Hello! This is a test of the text to speech system.",
        "The agent project is a sophisticated AI-powered codebase assistant.",
        "I can help you understand code, find bugs, and suggest improvements."
    ]
    
    for msg in messages:
        print(f"\n📝 Speaking: {msg}")
        await tts.text_to_speech(msg, play=True)
        await asyncio.sleep(0.5)
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(main())