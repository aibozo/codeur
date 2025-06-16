#!/usr/bin/env python3
"""
Test TTS voice mode with simple interaction.
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from src.voice_agent.tts_voice_mode import VoiceArchitect

# Load environment variables
load_dotenv()

async def main():
    print("🎤 Testing TTS Voice Architect")
    print("=" * 50)
    
    # Create voice architect
    voice_architect = VoiceArchitect(
        project_path=Path.cwd(),
        voice_name="Kore"
    )
    
    # Test a simple request
    print("\n📝 Testing request: 'What is the main purpose of this project?'")
    response = await voice_architect.process_request(
        "What is the main purpose of this project?",
        voice_output=True
    )
    print(f"\n🤖 Response: {response}")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(main())