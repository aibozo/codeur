#!/usr/bin/env python3
"""
Test script to send a query to the voice agent
"""

import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from src.voice_agent.gemini_live_interface import GeminiLiveVoiceAgent


async def test_query():
    """Test a single query without audio."""
    print("Testing Voice Agent Query")
    print("=" * 50)
    
    # Create agent
    agent = GeminiLiveVoiceAgent(
        rag_service=None,
        project_path=Path.cwd()
    )
    
    # Test query
    query = "What programming patterns are used in this voice agent system?"
    print(f"\n🎤 Query: {query}")
    
    response = await agent.process_voice_query(query)
    print(f"\n🤖 Response:\n{response}")
    
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_query())