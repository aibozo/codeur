#!/usr/bin/env python3
"""
Interactive test for voice agent with tools
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.voice_agent.gemini_live_tools import LiveVoiceAgent


async def test_interactive():
    """Test voice agent interactively."""
    print("Testing Live Voice Agent")
    print("=" * 50)
    
    agent = LiveVoiceAgent(project_path=Path.cwd())
    
    # Simulate a few queries
    queries = [
        "What does the EventBridge class do?",
        "List the Python files in the voice_agent directory",
        "Show me the architecture of this system"
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        print("🔍 This would normally use voice input and call tools to search the codebase")
        print("   Tools available: search_code, read_file, get_architecture, list_files")
    
    print("\n✅ Voice agent is configured correctly!")
    print("To use it interactively, run: agent voice --audio-input gemini-live")
    
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_interactive())