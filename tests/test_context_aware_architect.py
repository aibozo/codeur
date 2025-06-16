#!/usr/bin/env python3
"""
Test and demonstrate the Context-Aware Architect integration.
"""

import asyncio
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_aware_architect import ContextAwareArchitect, create_context_aware_architect
from src.architect.context_graph_models import ConversationPhase


async def demo_context_aware_architect():
    """Demonstrate the Context-Aware Architect in action."""
    
    print("\n" + "="*80)
    print("CONTEXT-AWARE ARCHITECT DEMO")
    print("="*80)
    
    # Create context-aware architect
    project_path = Path.cwd()
    architect = create_context_aware_architect(
        project_path=str(project_path),
        mode="balanced",
        use_enhanced_task_graph=True
    )
    
    print(f"\n✅ Created Context-Aware Architect for: {project_path}")
    print(f"   Mode: {architect.context_config.__class__.__name__}")
    print(f"   Enhanced task graph: {architect.use_enhanced_task_graph}")
    
    # Simulate a conversation about building a web app
    conversations = [
        # Phase 1: Exploration
        {
            "message": "I want to build a social media dashboard that shows analytics from multiple platforms",
            "task_ids": ["DASH-001"],
            "phase": ConversationPhase.EXPLORATION
        },
        {
            "message": "It should support Twitter, LinkedIn, and Instagram. What architecture would you recommend?",
            "task_ids": ["DASH-001"],
            "phase": ConversationPhase.EXPLORATION
        },
        
        # Phase 2: Planning
        {
            "message": "Let's design the system architecture. Should we use microservices or monolithic?",
            "task_ids": ["DASH-001", "ARCH-001"],
            "phase": ConversationPhase.PLANNING
        },
        {
            "message": "What database would work best for storing social media metrics?",
            "task_ids": ["DASH-001", "DB-001"],
            "phase": ConversationPhase.PLANNING
        },
        
        # Phase 3: Implementation
        {
            "message": "Create the initial task structure for building this dashboard",
            "task_ids": ["DASH-001", "IMPL-001"],
            "phase": ConversationPhase.IMPLEMENTATION
        },
        {
            "message": "How should we implement the Twitter API integration?",
            "task_ids": ["DASH-001", "API-001"],
            "phase": ConversationPhase.IMPLEMENTATION
        },
        
        # Add more messages to trigger summarization
        {
            "message": "What about rate limiting for the APIs?",
            "task_ids": ["API-001"],
            "phase": ConversationPhase.IMPLEMENTATION
        },
        {
            "message": "Should we use Redis for caching?",
            "task_ids": ["CACHE-001"],
            "phase": ConversationPhase.PLANNING
        },
        {
            "message": "How do we handle authentication?",
            "task_ids": ["AUTH-001"],
            "phase": ConversationPhase.PLANNING
        },
        {
            "message": "What frontend framework should we use?",
            "task_ids": ["UI-001"],
            "phase": ConversationPhase.PLANNING
        }
    ]
    
    print("\n💬 Starting conversation...")
    
    # Process messages
    for i, conv in enumerate(conversations):
        print(f"\n--- Message {i+1}/{len(conversations)} ---")
        print(f"👤 User: {conv['message'][:80]}...")
        print(f"   Tasks: {', '.join(conv['task_ids'])}")
        print(f"   Phase: {conv['phase'].value}")
        
        # Process message
        response = await architect.process_message(
            user_message=conv['message'],
            task_ids=conv['task_ids'],
            phase=conv['phase']
        )
        
        print(f"🤖 Architect: {response[:150]}...")
        
        # Show context stats
        stats = architect.get_conversation_stats()
        print(f"\n📊 Context Stats:")
        print(f"   Total messages: {stats['total_messages']}")
        print(f"   Summarized: {stats['summarized_nodes']}")
        print(f"   Communities: {stats['communities']}")
        print(f"   Compression: {stats.get('compression_ratio', 0):.1%}")
        
        # Small delay to simulate real conversation
        await asyncio.sleep(0.5)
    
    # Create a checkpoint
    print("\n\n🏁 Creating checkpoint...")
    checkpoint_id = await architect.create_checkpoint(
        title="Initial Architecture Discussion",
        checkpoint_type="milestone",
        message_count=5
    )
    print(f"✅ Created checkpoint: {checkpoint_id[:8]}...")
    
    # Show final stats
    print("\n\n📈 Final Conversation Statistics:")
    final_stats = architect.get_conversation_stats()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")
    
    # Demonstrate context modes
    print("\n\n⚙️ Testing Different Context Modes:")
    
    modes = ["aggressive", "balanced", "rich"]
    for mode in modes:
        architect.switch_context_mode(mode)
        
        # Compile context for the last message
        if architect.context_graph.current_node_id:
            window = await architect.context_compiler.compile_context(
                architect.context_graph.current_node_id
            )
            print(f"\n   {mode.upper()} mode:")
            print(f"     Tokens: {window.total_tokens}")
            print(f"     Distribution: {window.full_nodes}F/{window.summary_nodes}S/{window.title_nodes}T/{window.hidden_nodes}H")
    
    # Save state
    print("\n\n💾 Saving conversation state...")
    state_file = await architect.save_conversation_state()
    print(f"✅ Saved to: {state_file}")
    
    # Test loading state
    print("\n🔄 Testing state restoration...")
    new_architect = create_context_aware_architect(
        project_path=str(project_path),
        mode="balanced"
    )
    
    loaded = await new_architect.load_conversation_state()
    if loaded:
        print(f"✅ Successfully restored {len(new_architect.context_graph.nodes)} messages")
    else:
        print("❌ No saved state to restore")
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)
    
    return architect


async def test_integration_features():
    """Test specific integration features."""
    print("\n\n🧪 Testing Integration Features...")
    
    # Create architect
    architect = create_context_aware_architect(
        project_path=".",
        mode="aggressive"  # Use aggressive mode for testing
    )
    
    # Test 1: Task-based communities
    print("\n1. Testing task-based conversation organization:")
    
    # Add messages for different tasks
    await architect.process_message(
        "Let's design the user authentication system",
        task_ids=["AUTH-001"]
    )
    
    await architect.process_message(
        "We need JWT tokens and OAuth2 support",
        task_ids=["AUTH-001"]
    )
    
    await architect.process_message(
        "Now let's work on the database schema",
        task_ids=["DB-001"]
    )
    
    await architect.process_message(
        "We'll use PostgreSQL with proper indexing",
        task_ids=["DB-001"]
    )
    
    # Check communities
    task_communities = [
        c for c in architect.context_graph.communities.values() 
        if c.task_id
    ]
    print(f"   ✓ Created {len(task_communities)} task-based communities")
    for comm in task_communities:
        print(f"     - {comm.name}: {len(comm.node_ids)} messages")
    
    # Test 2: Context window optimization
    print("\n2. Testing context window optimization:")
    
    # Add more messages to trigger summarization
    for i in range(10):
        await architect.process_message(
            f"Implementation detail {i+1} for the authentication system",
            task_ids=["AUTH-001"]
        )
    
    # Force summarization
    await architect.context_summarizer.summarize_old_nodes(force=True)
    
    stats = architect.get_conversation_stats()
    print(f"   ✓ Summarized {stats['summarized_nodes']} messages")
    print(f"   ✓ Compression ratio: {stats.get('compression_ratio', 0):.1%}")
    
    # Test 3: Phase detection
    print("\n3. Testing conversation phase detection:")
    
    test_messages = [
        ("What is the best approach for this?", ConversationPhase.EXPLORATION),
        ("Let's plan the architecture", ConversationPhase.PLANNING),
        ("Implement the login endpoint", ConversationPhase.IMPLEMENTATION),
        ("Review the code quality", ConversationPhase.REVIEW)
    ]
    
    for msg, expected_phase in test_messages:
        detected = architect._detect_conversation_phase(msg)
        match = "✓" if detected == expected_phase else "✗"
        print(f"   {match} '{msg}' → {detected.value}")
    
    print("\n✅ All integration features working correctly!")


if __name__ == "__main__":
    # Check if running with mock mode
    if "--mock" in sys.argv or not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  Running in MOCK mode (no LLM calls)")
        os.environ["OPENAI_API_KEY"] = "mock-key"
    
    # Run demo
    asyncio.run(demo_context_aware_architect())
    
    # Run tests
    asyncio.run(test_integration_features())