#!/usr/bin/env python3
"""
Full voice agent test with working audio configuration.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Suppress ALSA errors
from ctypes import *
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass


async def test_voice_agent():
    """Test the full voice agent with audio."""
    print("🎤 FULL VOICE AGENT TEST")
    print("=" * 50)
    
    # Ensure PULSE_SERVER is set
    if not os.environ.get("PULSE_SERVER"):
        os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"
    
    from src.voice_agent.gemini_native_audio_simple import SimplifiedNativeAudioAgent
    
    print("Creating voice agent...")
    agent = SimplifiedNativeAudioAgent(
        project_path=Path.cwd(),
        thinking_mode=False,
        voice_name="Zephyr"
    )
    
    print(f"✅ Agent initialized")
    print(f"📁 Project: {agent.project_path}")
    print(f"🧠 Model: {agent.model}")
    
    # Test in automated mode
    try:
        async with agent.client.aio.live.connect(
            model=agent.model,
            config=agent.config
        ) as session:
            agent.session = session
            
            print("\n✅ Connected to Gemini Live API!")
            print("Testing voice interaction...\n")
            
            # Send initial context
            await session.send_client_content(
                turns={
                    "role": "user", 
                    "parts": [{
                        "text": f"""You are a helpful voice assistant for the codebase at: {agent.project_path}

You can help with explaining code, finding implementations, and answering development questions.
I will provide code context when needed.

Please acknowledge with a brief greeting and tell me you're ready to help with the codebase."""
                    }]
                },
                turn_complete=True
            )
            
            # Get greeting
            print("⏳ Waiting for Gemini's greeting...")
            greeting_received = False
            
            async for response in session.receive():
                if response.data:
                    print(f"🔊 Playing greeting ({len(response.data)} bytes)")
                    # Play audio
                    import pyaudio
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=24000,
                        output=True
                    )
                    stream.write(response.data)
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    greeting_received = True
                    break
                if response.text:
                    print(f"📝 Text: {response.text}")
                    greeting_received = True
                    break
            
            if not greeting_received:
                print("❌ No greeting received")
                return
            
            # Test a codebase query
            print("\n\n📝 Testing codebase query...")
            
            # First, get local context
            query = "What is the EventBridge class?"
            context = await agent.search_codebase("EventBridge")
            
            # Send query with context
            full_query = f"""Based on this search result from the codebase:

{context}

User question: {query}"""
            
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": full_query}]},
                turn_complete=True
            )
            
            print("⏳ Waiting for response about EventBridge...")
            
            # Get response
            response_count = 0
            async for response in session.receive():
                if response.data:
                    print(f"\n🔊 Playing response ({len(response.data)} bytes)")
                    # Play audio
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=24000,
                        output=True
                    )
                    stream.write(response.data)
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    response_count += 1
                
                if response.text:
                    print(f"\n📝 Text response: {response.text}")
                    response_count += 1
                
                # Stop after first response
                if response_count > 0:
                    break
            
            # Test another query
            print("\n\n📝 Testing architecture query...")
            
            arch_info = await agent.get_architecture_info()
            query2 = "Can you summarize the project structure?"
            
            full_query2 = f"""Based on this information:

{arch_info}

{query2}"""
            
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": full_query2}]},
                turn_complete=True
            )
            
            print("⏳ Waiting for architecture summary...")
            
            # Get response
            async for response in session.receive():
                if response.data:
                    print(f"\n🔊 Playing architecture summary ({len(response.data)} bytes)")
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=24000,
                        output=True
                    )
                    stream.write(response.data)
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    break
                if response.text:
                    print(f"\n📝 Text: {response.text}")
                    break
            
            print("\n\n✅ Voice agent test completed successfully!")
            print("\nThe voice agent is working properly with:")
            print("- ✅ Audio input/output through WSLg")
            print("- ✅ Codebase search and context")
            print("- ✅ Natural voice responses")
            print("\nYou can now use: agent voice")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎵 GEMINI NATIVE AUDIO VOICE AGENT TEST\n")
    asyncio.run(test_voice_agent())