"""
Example usage of the Voice Agent for codebase exploration.

This example demonstrates how to:
1. Set up a voice agent with RAG integration
2. Process voice queries about the codebase
3. Handle streaming audio input/output
4. Integrate with the agent system
"""

import asyncio
from pathlib import Path
import os
from typing import Optional

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.voice_agent import VoiceAgent, IntegratedVoiceAgent
from src.voice_agent.audio_interfaces import (
    OpenAIAudioInput, OpenAIAudioOutput,
    MockAudioInput, MockAudioOutput
)
from src.rag_service.adaptive_rag_service import AdaptiveRAGService
from src.core.integrated_agent_base import AgentContext
from src.core.event_bridge import EventBridge
from src.core.message_bus import MessageBus
from src.core.realtime import RealtimeService
from src.core.settings import Settings


async def example_basic_voice_agent():
    """Example of basic voice agent usage."""
    print("\n=== Basic Voice Agent Example ===\n")
    
    # Set up project path
    project_path = Path.cwd()
    
    # Initialize RAG service
    rag_service = AdaptiveRAGService(
        persist_directory=str(project_path / ".rag"),
        repo_path=str(project_path),
        enable_adaptive_gating=True
    )
    
    # Initialize audio interfaces
    # Use mock interfaces for demo (replace with OpenAI for real usage)
    audio_input = MockAudioInput()
    audio_output = MockAudioOutput()
    
    # For real OpenAI usage:
    # audio_input = OpenAIAudioInput(api_key=os.getenv("OPENAI_API_KEY"))
    # audio_output = OpenAIAudioOutput(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create voice agent
    voice_agent = VoiceAgent(
        rag_service=rag_service,
        audio_input=audio_input,
        audio_output=audio_output,
        project_path=project_path
    )
    
    # Example 1: Process text query
    print("Example 1: Text Query")
    response = await voice_agent.process_text(
        "What does the RAG service do in this codebase?",
        session_id="demo_session",
        synthesize_response=True
    )
    
    print(f"Response: {response.text[:200]}...")
    print(f"Source files: {response.source_files[:3]}")
    print(f"Has audio: {response.audio is not None}")
    
    # Example 2: Process another query in same session
    print("\nExample 2: Follow-up Query")
    response2 = await voice_agent.process_text(
        "How does it integrate with the adaptive similarity gate?",
        session_id="demo_session",
        synthesize_response=True
    )
    
    print(f"Response: {response2.text[:200]}...")
    
    # Example 3: Get session summary
    print("\nExample 3: Session Summary")
    summary = voice_agent.get_session_summary("demo_session")
    print(f"Session summary: {summary}")


async def example_integrated_voice_agent():
    """Example of integrated voice agent with full system."""
    print("\n\n=== Integrated Voice Agent Example ===\n")
    
    # Set up infrastructure
    project_path = Path.cwd()
    settings = Settings()
    message_bus = MessageBus()
    realtime_service = RealtimeService(message_bus)
    event_bridge = EventBridge(message_bus, realtime_service)
    
    # Initialize RAG service
    rag_service = AdaptiveRAGService(
        persist_directory=str(project_path / ".rag"),
        repo_path=str(project_path)
    )
    
    # Create agent context
    context = AgentContext(
        project_path=project_path,
        event_bridge=event_bridge,
        rag_client=type('RAGClient', (), {'service': rag_service})(),  # Mock RAG client
        agent_id="voice_agent_001"
    )
    
    # Initialize audio interfaces
    audio_input = MockAudioInput()
    audio_output = MockAudioOutput()
    
    # Create integrated voice agent
    voice_agent = IntegratedVoiceAgent(
        context=context,
        audio_input=audio_input,
        audio_output=audio_output
    )
    
    # Start a voice session
    print("Starting voice session...")
    session_data = await voice_agent.start_voice_session(
        "integrated_demo",
        user_preferences={"voice": "nova", "speed": 1.0}
    )
    
    print(f"Session started: {session_data['session_id']}")
    print(f"Welcome: {session_data['welcome_text']}")
    
    # Process voice input (simulated)
    print("\nProcessing voice query...")
    mock_audio = b"MOCK_AUDIO_DATA"
    
    response = await voice_agent.process_voice_input(
        "integrated_demo",
        mock_audio
    )
    
    print(f"Response: {response.text}")
    
    # Get codebase overview
    print("\nGetting codebase overview...")
    overview = await voice_agent.get_codebase_overview("integrated_demo")
    print(f"Overview: {overview.text[:300]}...")
    
    # End session
    print("\nEnding session...")
    end_summary = await voice_agent.end_voice_session("integrated_demo")
    print(f"Session ended: {end_summary}")


async def example_streaming_interaction():
    """Example of streaming audio interaction."""
    print("\n\n=== Streaming Audio Example ===\n")
    
    from src.voice_agent.audio_interfaces import AudioChunk
    
    # Set up voice agent (using basic setup for simplicity)
    project_path = Path.cwd()
    rag_service = AdaptiveRAGService(
        persist_directory=str(project_path / ".rag"),
        repo_path=str(project_path)
    )
    
    audio_input = MockAudioInput()
    audio_output = MockAudioOutput()
    
    voice_agent = VoiceAgent(
        rag_service=rag_service,
        audio_input=audio_input,
        audio_output=audio_output,
        project_path=project_path
    )
    
    # Simulate streaming audio chunks
    async def audio_stream_generator():
        """Generate mock audio stream."""
        for i in range(5):
            chunk = AudioChunk(
                data=f"CHUNK_{i}".encode(),
                timestamp=asyncio.get_event_loop().time(),
                is_final=(i == 4)
            )
            yield chunk
            await asyncio.sleep(0.1)
    
    print("Processing streaming audio...")
    response_count = 0
    
    async for response in voice_agent.stream_response(
        audio_stream_generator(),
        "streaming_session"
    ):
        response_count += 1
        print(f"Streaming response {response_count}: {response.text}")
    
    print("\nStreaming complete!")


async def example_code_specific_queries():
    """Example of code-specific voice queries."""
    print("\n\n=== Code-Specific Queries Example ===\n")
    
    # Set up voice agent
    project_path = Path.cwd()
    rag_service = AdaptiveRAGService(
        persist_directory=str(project_path / ".rag"),
        repo_path=str(project_path)
    )
    
    voice_agent = VoiceAgent(
        rag_service=rag_service,
        audio_input=MockAudioInput(),
        audio_output=MockAudioOutput(),
        project_path=project_path
    )
    
    # Example queries
    queries = [
        "Explain the function search_code in the RAG service",
        "Where is the IntegratedAgentBase class implemented?",
        "List all functions in the voice_agent.py file",
        "How does the WebSocket handler work?",
        "Find where EventBridge is used"
    ]
    
    session_id = "code_query_session"
    
    for i, query in enumerate(queries, 1):
        print(f"\nQuery {i}: {query}")
        response = await voice_agent.process_text(
            query,
            session_id,
            synthesize_response=False
        )
        
        print(f"Intent: {response.metadata.get('intent', 'unknown')}")
        print(f"Response: {response.text[:150]}...")
        if response.source_files:
            print(f"Related files: {', '.join(response.source_files[:3])}")


async def main():
    """Run all examples."""
    try:
        # Run basic example
        await example_basic_voice_agent()
        
        # Run integrated example
        await example_integrated_voice_agent()
        
        # Run streaming example
        await example_streaming_interaction()
        
        # Run code-specific queries
        await example_code_specific_queries()
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())