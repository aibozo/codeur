#!/usr/bin/env python3
"""
Test the integrated WebSocket voice agent with tools and architecture.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


async def main():
    """Test the integrated voice agent."""
    print("🎤 INTEGRATED VOICE AGENT TEST")
    print("=" * 50)
    
    from src.voice_agent.gemini_native_audio_simple import WebSocketVoiceAgent
    
    # Create agent
    agent = WebSocketVoiceAgent(project_path=Path.cwd())
    
    print(f"Architecture loaded: {len(agent.architecture_context)} chars")
    print(f"Tools available: {len(agent.tools[0]['functionDeclarations']) if agent.tools else 0}")
    if agent.tools:
        tool_names = [t['name'] for t in agent.tools[0]['functionDeclarations']]
        print(f"Tool functions: {', '.join(tool_names[:5])}{'...' if len(tool_names) > 5 else ''}")
    print("")
    
    # Run the agent
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user")