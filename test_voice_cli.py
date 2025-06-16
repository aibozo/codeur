#!/usr/bin/env python3
"""
Test voice agent CLI with text input/output mode.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def test_voice_agent_text_mode():
    """Test voice agent with text I/O to bypass audio issues."""
    print("🎤 Voice Agent Text Mode Test")
    print("=" * 50)
    
    from src.voice_agent.gemini_native_audio import NativeAudioVoiceAgent
    
    # Create agent without audio streams
    agent = NativeAudioVoiceAgent(
        project_path=Path.cwd(),
        thinking_mode=True,
        thinking_budget=4096
    )
    
    # Mock PyAudio to avoid errors
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
    
    agent.pya = MockPyAudio()
    
    print(f"✅ Agent initialized")
    print(f"🧠 Model: {agent.model}")
    print(f"💭 Thinking budget: {agent.thinking_budget}")
    print(f"🔧 Tools: {', '.join(agent.tools[i]['name'] for i in range(len(agent.tools)))}")
    
    # Test direct API connection
    try:
        from google import genai
        
        async with agent.client.aio.live.connect(
            model=agent.model,
            config=agent.config
        ) as session:
            print("\n✅ Connected to Gemini Live API!")
            
            # Send initial context
            await session.send_client_content(
                turns={
                    "role": "user",
                    "parts": [{
                        "text": """You are a helpful voice assistant for a codebase.
                        
When I ask questions, use the available tools to search and analyze code.
Available tools: search_codebase, read_file, get_architecture, share_code

Please acknowledge that you understand."""
                    }]
                },
                turn_complete=True
            )
            
            # Get acknowledgment
            print("\n⏳ Waiting for acknowledgment...")
            ack_received = False
            
            async for response in session.receive():
                if response.text:
                    print(f"\n🤖 Gemini: {response.text}")
                    ack_received = True
                    break
                if response.data:
                    print(f"\n🔊 (Received {len(response.data)} bytes of audio)")
                    ack_received = True
                    break
            
            if not ack_received:
                print("❌ No acknowledgment received")
                return
            
            # Test a simple query
            print("\n📝 Sending test query...")
            await session.send_client_content(
                turns={
                    "role": "user",
                    "parts": [{
                        "text": "What voice-related files are in this codebase? Please search for voice agent implementations."
                    }]
                },
                turn_complete=True
            )
            
            # Listen for responses and tool calls
            print("\n⏳ Waiting for response...")
            response_count = 0
            tool_calls = 0
            
            import time
            start_time = time.time()
            
            async for msg in session.receive():
                # Handle text
                if msg.text:
                    print(f"\n🤖 Response: {msg.text}")
                    response_count += 1
                
                # Handle audio
                if msg.data:
                    print(f"\n🔊 Audio response: {len(msg.data)} bytes")
                    response_count += 1
                
                # Check for tool calls in server content
                if hasattr(msg, 'server_content') and msg.server_content:
                    if hasattr(msg.server_content, 'tool_call') and msg.server_content.tool_call:
                        tool_call = msg.server_content.tool_call
                        print(f"\n🔧 Tool call: {tool_call.name}")
                        print(f"   Args: {tool_call.args}")
                        tool_calls += 1
                        
                        # Simulate tool response
                        if tool_call.name == "search_codebase":
                            await session.send_tool_response(
                                tool_call_id=tool_call.id,
                                response={
                                    "success": True,
                                    "results": [
                                        {
                                            "file_path": "src/voice_agent/gemini_native_audio.py",
                                            "line_number": 1,
                                            "content": "Native Audio implementation for Gemini 2.5 Flash Live API",
                                            "relevance": 10
                                        },
                                        {
                                            "file_path": "src/cli/commands/voice.py", 
                                            "line_number": 44,
                                            "content": "def voice(project_path: Path, thinking: bool, voice: str, thinking_budget: int):",
                                            "relevance": 8
                                        }
                                    ],
                                    "count": 2
                                }
                            )
                            print("   ✅ Sent mock search results")
                
                # Timeout after 30 seconds
                if time.time() - start_time > 30:
                    print("\n⏱️ Timeout reached")
                    break
                
                # Stop after getting a good response
                if response_count >= 2 and tool_calls >= 1:
                    print("\n✅ Test successful!")
                    break
            
            print(f"\n📊 Summary:")
            print(f"   Responses: {response_count}")
            print(f"   Tool calls: {tool_calls}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_tool_handlers():
    """Test the tool handler functions directly."""
    print("\n\n🔧 Testing Tool Handlers")
    print("=" * 50)
    
    from src.voice_agent.gemini_native_audio import NativeAudioVoiceAgent
    
    agent = NativeAudioVoiceAgent(project_path=Path.cwd())
    
    # Test search_codebase
    print("\n1. Testing search_codebase:")
    result = await agent._handle_search_codebase({
        "query": "voice agent",
        "file_pattern": "**/*.py"
    })
    print(f"   Found {result.get('count', 0)} results")
    if result.get('success') and result.get('results'):
        for r in result['results'][:2]:
            print(f"   - {r['file_path']}:{r['line_number']}")
    
    # Test get_architecture
    print("\n2. Testing get_architecture:")
    result = await agent._handle_get_architecture({})
    if result.get('success'):
        print(f"   Source: {result.get('source')}")
        print(f"   Content preview: {result.get('content', '')[:100]}...")
    
    # Test share_code
    print("\n3. Testing share_code:")
    result = await agent._handle_share_code({
        "code": "def hello_world():\n    print('Hello from voice agent!')",
        "language": "python",
        "filename": "example.py"
    })
    if result.get('success'):
        print("   Formatted code:")
        print(result.get('formatted_code'))


if __name__ == "__main__":
    print("🎵 VOICE AGENT CLI TEST\n")
    
    # Run tests
    asyncio.run(test_voice_agent_text_mode())
    asyncio.run(test_tool_handlers())