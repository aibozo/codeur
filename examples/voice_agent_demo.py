#!/usr/bin/env python3
"""
Voice Agent Demo - Natural Language Codebase Interaction

This script demonstrates how to use the voice agent to interact with
a codebase using natural language queries.

Requirements:
    - For Gemini Live: pip install google-genai pyaudio
    - For OpenAI: pip install openai
    - Set appropriate API keys in environment variables
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.voice_agent import VoiceAgent, MockAudioInput, MockAudioOutput
from src.voice_agent.gemini_live_interface import GeminiLiveVoiceAgent
from src.rag_service import AdaptiveRAGService


async def demo_basic_voice_agent():
    """Demo basic voice agent with mock audio."""
    print("=== Basic Voice Agent Demo ===\n")
    
    # Initialize RAG service (assuming index exists)
    project_path = Path.cwd()
    rag_dir = project_path / ".rag"
    
    if not rag_dir.exists():
        print("No RAG index found. Please run 'agent index' first.")
        return
    
    rag_service = AdaptiveRAGService(
        persist_directory=str(rag_dir),
        repo_path=str(project_path),
        enable_adaptive_gating=True
    )
    
    # Create voice agent with mock audio
    voice_agent = VoiceAgent(
        rag_service=rag_service,
        audio_input=MockAudioInput(),
        audio_output=MockAudioOutput(),
        project_path=project_path
    )
    
    # Example queries
    queries = [
        "What does the EventBridge class do?",
        "Where is the RAG service implemented?",
        "How does the task graph work?",
        "Find usages of the MessageBus",
        "Help me debug the voice agent"
    ]
    
    session_id = "demo_session"
    
    for query in queries:
        print(f"\n🎤 User: {query}")
        response = await voice_agent.process_text(query, session_id)
        print(f"🤖 Assistant: {response[:200]}..." if len(response) > 200 else f"🤖 Assistant: {response}")
    
    # Show session summary
    summary = voice_agent.get_session_summary(session_id)
    print(f"\n📊 Session Summary:")
    print(f"  - Messages: {summary['message_count']}")
    print(f"  - Duration: {summary['duration']:.1f}s")
    print(f"  - Files mentioned: {len(summary['mentioned_files'])}")
    print(f"  - Functions mentioned: {len(summary['mentioned_functions'])}")


async def demo_gemini_live():
    """Demo Gemini Live API integration."""
    print("=== Gemini Live Voice Agent Demo ===\n")
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("❌ GEMINI_API_KEY or GOOGLE_API_KEY not set")
        print("Set with: export GEMINI_API_KEY=your-key")
        return
    
    # Initialize RAG service
    project_path = Path.cwd()
    rag_dir = project_path / ".rag"
    rag_service = None
    
    if rag_dir.exists():
        rag_service = AdaptiveRAGService(
            persist_directory=str(rag_dir),
            repo_path=str(project_path),
            enable_adaptive_gating=True
        )
        print("✓ RAG index loaded")
    else:
        print("⚠ No RAG index - voice agent will work without code search")
    
    # Create Gemini Live agent
    try:
        agent = GeminiLiveVoiceAgent(
            rag_service=rag_service,
            project_path=project_path
        )
        
        print("\n🎤 Gemini Live Voice Agent Ready!")
        print("📁 Project:", project_path)
        print("\nThis would normally start audio streaming.")
        print("For this demo, we'll process text queries:\n")
        
        # Demo text queries
        queries = [
            "What does EventBridge do?",
            "Show me the voice agent implementation",
            "How do I use the RAG service?"
        ]
        
        for query in queries:
            print(f"🎤 User: {query}")
            response = await agent.process_voice_query(query)
            print(f"🤖 Assistant: {response}\n")
        
        agent.cleanup()
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Install with: pip install google-genai pyaudio")
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_integrated_voice_agent():
    """Demo integrated voice agent with full system integration."""
    print("=== Integrated Voice Agent Demo ===\n")
    
    from src.core.integrated_agent_base import AgentContext
    from src.voice_agent import IntegratedVoiceAgent
    
    # Create mock context
    context = AgentContext(
        agent_id="voice_agent_demo",
        project_path=Path.cwd(),
        rag_client=None,  # Would normally have RAG client
        event_bridge=None,  # Would normally have event bridge
        task_manager=None  # Would normally have task manager
    )
    
    # Create integrated agent
    agent = IntegratedVoiceAgent(context)
    
    # Set mock audio interfaces
    agent.set_audio_interfaces(MockAudioInput(), MockAudioOutput())
    
    session_id = "integrated_demo"
    
    # Test different command types
    commands = [
        # Direct query
        ("What is the purpose of the message bus?", "direct"),
        # Task creation
        ("Implement a new caching system for the RAG service", "task"),
        # Multi-agent collaboration
        ("Analyze and fix the performance issues in the voice agent", "collaborative")
    ]
    
    for command, expected_type in commands:
        print(f"\n🎤 User: {command}")
        print(f"   (Expected: {expected_type} response)")
        
        result = await agent.process_voice_command(command, session_id)
        
        print(f"🤖 Response type: {result['type']}")
        print(f"🤖 Assistant: {result['response'][:200]}..." if len(result['response']) > 200 else f"🤖 Assistant: {result['response']}")
        
        if result['type'] == 'task_created':
            print(f"   Task ID: {result.get('task_id')}")
        elif result['type'] == 'collaborative_response':
            print(f"   Agents involved: {', '.join(result.get('agents_involved', []))}")
    
    # Get insights
    insights = await agent.get_voice_insights()
    print(f"\n📊 Voice Agent Insights:")
    print(f"  - Total sessions: {insights['total_sessions']}")
    print(f"  - Active sessions: {insights['active_sessions']}")
    print(f"  - Total commands: {insights['total_commands']}")
    print(f"  - Common queries: {insights['common_queries'][:3]}")


async def main():
    """Run all demos."""
    print("Voice Agent Demonstration")
    print("=" * 50)
    
    # Choose demo
    demos = {
        "1": ("Basic Voice Agent", demo_basic_voice_agent),
        "2": ("Gemini Live API", demo_gemini_live),
        "3": ("Integrated Voice Agent", demo_integrated_voice_agent)
    }
    
    print("\nAvailable demos:")
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect demo (1-3) or 'all' for all demos: ").strip()
    
    if choice == 'all':
        for name, demo_func in demos.values():
            print(f"\n{'=' * 50}")
            await demo_func()
    elif choice in demos:
        _, demo_func = demos[choice]
        await demo_func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())