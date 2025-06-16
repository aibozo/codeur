#!/usr/bin/env python3
"""
Test voice mode integration between frontend and backend.
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


async def test_tts_generation():
    """Test TTS generation directly."""
    print("Testing TTS generation...")
    
    tts = TTSVoiceMode()
    
    # Test short response
    text = "Hello! I've analyzed your project structure. It has 3 main components and follows a microservices architecture."
    
    audio_file = await tts.text_to_speech(text, play=False)
    
    if audio_file:
        print(f"✅ Audio generated: {audio_file}")
        print(f"   File size: {os.path.getsize(audio_file)} bytes")
    else:
        print("❌ Failed to generate audio")


async def test_voice_architect_response():
    """Test architect with voice-friendly response."""
    print("\nTesting voice-friendly architect response...")
    
    # This would normally come from the API
    normal_response = """I'll design a comprehensive architecture for your e-commerce platform. 
    
    The system will consist of the following main components:
    1. Frontend Service: React-based web application with responsive design
    2. API Gateway: Node.js Express server handling routing and authentication
    3. User Service: Manages user accounts, authentication, and profiles
    4. Product Service: Handles product catalog, inventory, and search
    5. Order Service: Processes orders, payments, and order tracking
    6. Notification Service: Sends emails, SMS, and push notifications
    
    The architecture follows microservices patterns with each service having its own database.
    Communication between services will use REST APIs with potential for event-driven messaging using RabbitMQ for asynchronous operations.
    
    I've created a task graph with 24 tasks across 4 phases. The critical path contains 8 tasks."""
    
    voice_response = """I'll design a comprehensive architecture for your e-commerce platform.

The system will have six main components. First, a React frontend for users. Second, an API gateway for routing. Third, a user service for accounts. Fourth, a product service for the catalog. Fifth, an order service for purchases. And sixth, a notification service for updates.

Each service gets its own database. They'll communicate through REST APIs, with message queuing for background tasks.

I've created 24 tasks in 4 phases. The critical path has 8 key tasks to complete."""
    
    print("\nOriginal response (for text):")
    print("-" * 50)
    print(normal_response)
    print("\nVoice-friendly response:")
    print("-" * 50)
    print(voice_response)
    
    # Generate TTS for voice response
    tts = TTSVoiceMode()
    audio_file = await tts.text_to_speech(voice_response, play=True)
    
    if audio_file:
        print(f"\n✅ Voice response generated and played: {audio_file}")
    else:
        print("\n❌ Failed to generate voice response")


if __name__ == "__main__":
    print("Voice Mode Integration Test")
    print("=" * 60)
    
    asyncio.run(test_tts_generation())
    asyncio.run(test_voice_architect_response())