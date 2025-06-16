#!/usr/bin/env python3
"""
Test enhanced voice agent
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.voice_agent.gemini_live_enhanced import EnhancedLiveVoiceAgent


async def test_enhanced():
    """Test enhanced voice agent."""
    print("Testing Enhanced Voice Agent")
    print("=" * 50)
    
    agent = EnhancedLiveVoiceAgent(project_path=Path.cwd())
    
    # Test query processing
    queries = [
        "What does EventBridge do?",
        "Show me the architecture",
        "Search for RAG service"
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        context = await agent.process_query(query)
        if context:
            print("📚 Context gathered:")
            print(context[:200] + "..." if len(context) > 200 else context)
        else:
            print("❌ No context found")
    
    print("\n✅ Query processing works!")
    agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_enhanced())