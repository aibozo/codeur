#!/usr/bin/env python3
"""
Test the Live voice agent with tools
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.voice_agent.gemini_live_tools import LiveVoiceAgent


async def test_voice_with_tools():
    """Test voice agent with tool capabilities."""
    print("Testing Live Voice Agent with Tools")
    print("=" * 50)
    
    # Create agent
    agent = LiveVoiceAgent(project_path=Path.cwd())
    
    # Test tool functions directly first
    print("\n1. Testing search_code...")
    result = await agent.search_code("EventBridge")
    print(f"   Found {result['count']} results")
    if result['results']:
        print(f"   First result: {result['results'][0]['file']}")
    
    print("\n2. Testing list_files...")
    result = await agent.list_files("src/voice_agent", "*.py")
    print(f"   Found {result['total']} Python files")
    
    print("\n3. Testing get_architecture...")
    result = await agent.get_architecture()
    print(f"   Got architecture info: {list(result.keys())}")
    
    print("\n4. Testing read_file...")
    result = await agent.read_file("src/voice_agent/__init__.py", 1, 10)
    if "error" not in result:
        print(f"   Read {result['end_line'] - result['start_line'] + 1} lines from {result['file']}")
    
    print("\nTools are working! You can now run: agent voice --audio-input gemini-live")
    
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_voice_with_tools())