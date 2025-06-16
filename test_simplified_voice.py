#!/usr/bin/env python3
"""
Test the simplified voice agent.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def test_simplified_agent():
    """Test simplified agent connection."""
    print("🎤 Testing Simplified Voice Agent")
    print("=" * 50)
    
    from src.voice_agent.gemini_native_audio_simple import SimplifiedNativeAudioAgent
    
    # Mock PyAudio to avoid ALSA errors
    class MockPyAudio:
        def __init__(self):
            pass
        def terminate(self):
            pass
        def get_default_input_device_info(self):
            return {"name": "Mock Microphone", "index": 0}
        def open(self, **kwargs):
            return MockStream()
    
    class MockStream:
        def stop_stream(self):
            pass
        def close(self):
            pass
        def read(self, size, exception_on_overflow=False):
            # Return silence
            import numpy as np
            return np.zeros(size, dtype=np.int16).tobytes()
        def write(self, data):
            pass
    
    # Create agent with mock audio
    agent = SimplifiedNativeAudioAgent(
        project_path=Path.cwd(),
        thinking_mode=False
    )
    
    # Replace PyAudio with mock
    agent.pya = MockPyAudio()
    
    print(f"✅ Agent created")
    print(f"🧠 Model: {agent.model}")
    
    # Test local functions
    print("\n📊 Testing local functions:")
    
    # Test search
    print("\n1. Testing search:")
    result = await agent.search_codebase("voice agent")
    print(result[:200] + "..." if len(result) > 200 else result)
    
    # Test architecture
    print("\n2. Testing architecture:")
    result = await agent.get_architecture_info()
    print(result[:200] + "..." if len(result) > 200 else result)
    
    # Test query processing
    print("\n3. Testing query processing:")
    queries = [
        "search for EventBridge",
        "show architecture",
        "what is the voice agent?"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        result = await agent.process_query(query)
        if result:
            print(f"   Local result: {result[:100]}...")
        else:
            print("   Would send to Gemini")
    
    # Test API connection
    print("\n\n4. Testing API connection:")
    try:
        async with agent.client.aio.live.connect(
            model=agent.model,
            config=agent.config
        ) as session:
            print("✅ Connected to Gemini Live API!")
            
            # Send test message
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Say hello"}]},
                turn_complete=True
            )
            
            # Get one response
            async for response in session.receive():
                if response.text:
                    print(f"📝 Text response: {response.text}")
                    break
                if response.data:
                    print(f"🔊 Audio response: {len(response.data)} bytes")
                    break
                    
    except Exception as e:
        print(f"❌ API Error: {e}")


if __name__ == "__main__":
    print("🎵 SIMPLIFIED VOICE AGENT TEST\n")
    asyncio.run(test_simplified_agent())