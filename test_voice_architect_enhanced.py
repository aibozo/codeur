#!/usr/bin/env python3
"""
Test enhanced voice mode with the architect using better activation methods.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from src.voice_agent.voice_interface import VoiceInterface, ConversationLoop
from src.architect.architect import Architect


async def main():
    """Run enhanced voice architect."""
    print("🏗️  Voice Architect - Enhanced Mode")
    print("=" * 60)
    
    # Check which activation methods are available
    try:
        import keyboard
        has_keyboard = True
    except ImportError:
        has_keyboard = False
        print("⚠️  keyboard package not installed (push-to-talk unavailable)")
        print("   Install with: pip install keyboard")
    
    try:
        import pyaudio
        import numpy
        has_voice_detection = True
    except ImportError:
        has_voice_detection = False
        print("⚠️  pyaudio/numpy not installed (voice detection unavailable)")
        print("   Install with: pip install pyaudio numpy")
    
    print()
    
    # Choose activation method based on what's available
    if has_keyboard:
        activation = "push_to_talk"
        print("✅ Using Push-to-Talk mode (hold SPACE to record)")
    elif has_voice_detection:
        activation = "voice_activity"
        print("✅ Using Voice Activity Detection (just start speaking)")
    else:
        activation = "timeout"
        print("⚠️  Using timeout mode (5 second recordings)")
    
    # Initialize voice interface
    try:
        voice = VoiceInterface(
            activation_method=activation,
            hotkey="space",
            voice_threshold=0.02,  # Adjust based on your mic
            silence_duration=1.5   # Stop after 1.5s of silence
        )
    except Exception as e:
        print(f"❌ Failed to initialize voice interface: {e}")
        return
    
    # Initialize architect (simplified for demo)
    project_path = os.getcwd()
    architect_responses = {
        "help": "I can help you design system architectures, create task graphs, and plan your project. Just describe what you want to build!",
        "task": "I'll create a task breakdown for that. The main phases would be: 1) Design phase, 2) Implementation phase, 3) Testing phase, and 4) Deployment phase.",
        "architecture": "For that architecture, I recommend a microservices approach with separate frontend, API, and database layers. Each component should be independently scalable.",
        "default": "I understand. Let me analyze that requirement and create a plan for you. What specific features are most important?"
    }
    
    def process_architect_message(text: str) -> str:
        """Process message with architect-like responses."""
        text_lower = text.lower()
        
        if "help" in text_lower:
            return architect_responses["help"]
        elif "task" in text_lower or "plan" in text_lower:
            return architect_responses["task"]
        elif "architecture" in text_lower or "design" in text_lower:
            return architect_responses["architecture"]
        else:
            return architect_responses["default"]
    
    # Create conversation loop
    conversation = ConversationLoop(
        voice_interface=voice,
        process_message=process_architect_message,
        wake_word=None  # Could use "hey architect"
    )
    
    print("\n🎤 Voice mode ready!\n")
    
    # Run the conversation
    await conversation.run()


if __name__ == "__main__":
    asyncio.run(main())