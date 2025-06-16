#!/usr/bin/env python3
"""
Test the native audio voice agent implementation.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Test basic connection first
async def test_basic_connection():
    """Test basic connection to Live API."""
    print("Testing Basic Connection")
    print("=" * 50)
    
    from google import genai
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment")
        return False
    
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    # Test with standard model first
    model = "models/gemini-2.0-flash-live-001"
    config = {"response_modalities": ["TEXT"]}
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            print(f"✅ Connected to {model}")
            
            # Send a simple message
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Say hello"}]},
                turn_complete=True
            )
            
            # Get response
            async for response in session.receive():
                if response.text:
                    print(f"📥 Response: {response.text}")
                    return True
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_native_audio_model():
    """Test native audio model connection."""
    print("\n\nTesting Native Audio Model")
    print("=" * 50)
    
    from google import genai
    
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    # Test native audio model
    models = [
        "models/gemini-2.5-flash-preview-native-audio-dialog",
        "models/gemini-2.5-flash-exp-native-audio-thinking-dialog"
    ]
    
    for model in models:
        print(f"\n🧪 Testing: {model}")
        config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": "Zephyr"}
                }
            }
        }
        
        try:
            async with client.aio.live.connect(model=model, config=config) as session:
                print(f"✅ Connected!")
                
                # Send text, expect audio
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": "Say hello"}]},
                    turn_complete=True
                )
                
                # Wait for audio response
                import time
                start = time.time()
                
                async for response in session.receive():
                    if response.data:
                        print(f"✅ Got audio response: {len(response.data)} bytes")
                        return True
                    if response.text:
                        print(f"📝 Got text: {response.text}")
                    
                    if time.time() - start > 5:
                        print("⏱️ Timeout")
                        break
                        
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}...")


async def test_voice_agent():
    """Test the full voice agent."""
    print("\n\nTesting Voice Agent Implementation")
    print("=" * 50)
    
    try:
        from src.voice_agent.gemini_native_audio import create_voice_agent
        
        print("✅ Imports successful")
        
        # Create agent
        agent = create_voice_agent(
            project_path=Path.cwd(),
            thinking_mode=False
        )
        
        print(f"✅ Agent created with model: {agent.model}")
        print(f"📊 Tools available: {len(agent.tools)}")
        
        # Test tool handlers
        print("\n🔧 Testing tool handlers:")
        for tool_name in agent.tool_handlers:
            print(f"  - {tool_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_audio_streaming():
    """Test simple audio streaming."""
    print("\n\nTesting Audio Streaming")
    print("=" * 50)
    
    from google import genai
    from google.genai import types
    import numpy as np
    
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )
    
    model = "models/gemini-2.0-flash-live-001"
    config = {
        "response_modalities": ["TEXT"],
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False
            }
        }
    }
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✅ Connected with VAD enabled")
            
            # Send a tone
            sample_rate = 16000
            duration = 2.0
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # Simple "beep-beep" pattern
            freq1 = 440  # A4
            freq2 = 880  # A5
            
            # Create two beeps
            beep1 = np.sin(2 * np.pi * freq1 * t[:len(t)//4])
            silence1 = np.zeros(len(t)//4)
            beep2 = np.sin(2 * np.pi * freq2 * t[:len(t)//4])
            silence2 = np.zeros(len(t)//4)
            
            audio = np.concatenate([beep1, silence1, beep2, silence2])
            audio = (audio * 16384).astype(np.int16)
            
            print(f"📤 Sending {len(audio.tobytes())} bytes of audio (beep-beep pattern)")
            
            # Send audio
            await session.send_realtime_input(
                audio=types.Blob(
                    data=audio.tobytes(),
                    mime_type="audio/pcm;rate=16000"
                )
            )
            
            print("⏳ Waiting for VAD to process...")
            
            import time
            start = time.time()
            
            async for response in session.receive():
                if response.text:
                    print(f"✅ Response: {response.text}")
                    return True
                
                if time.time() - start > 10:
                    print("⏱️ Timeout - no response")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🎵 NATIVE AUDIO VOICE AGENT TEST\n")
    
    # Run tests in sequence
    asyncio.run(test_basic_connection())
    asyncio.run(test_native_audio_model())
    asyncio.run(test_voice_agent())
    asyncio.run(test_audio_streaming())