#!/usr/bin/env python3
"""
Example: Using the Context-Aware Architect for a project.

This example shows how to use the Context-Aware Architect to manage
long conversations efficiently while maintaining full context.
"""

import asyncio
import os
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_aware_architect import create_context_aware_architect
from src.architect.context_graph_models import ConversationPhase


async def main():
    """Example usage of Context-Aware Architect."""
    
    print("🏗️  Context-Aware Architect Example")
    print("=" * 50)
    
    # Create architect with balanced mode (good for most use cases)
    architect = create_context_aware_architect(
        project_path="./my_project",
        mode="balanced"  # Options: "aggressive", "balanced", "rich"
    )
    
    print("✅ Architect initialized\n")
    
    # Example 1: Simple conversation
    print("Example 1: Basic conversation")
    print("-" * 30)
    
    response = await architect.process_message(
        "I want to build a REST API for a todo list application"
    )
    print(f"User: I want to build a REST API for a todo list application")
    print(f"Architect: {response[:200]}...\n")
    
    # Example 2: Continuing with task context
    print("Example 2: Task-focused discussion")
    print("-" * 30)
    
    response = await architect.process_message(
        "What database should I use for this?",
        task_ids=["TODO-API-001"],  # Associate with a task
        phase=ConversationPhase.PLANNING
    )
    print(f"User: What database should I use for this?")
    print(f"Architect: {response[:200]}...\n")
    
    # Example 3: Multiple related tasks
    print("Example 3: Multi-task context")
    print("-" * 30)
    
    response = await architect.process_message(
        "How do I implement user authentication?",
        task_ids=["TODO-API-001", "AUTH-001"],  # Multiple tasks
        phase=ConversationPhase.IMPLEMENTATION,
        importance=0.8  # Higher importance for auth discussions
    )
    print(f"User: How do I implement user authentication?")
    print(f"Architect: {response[:200]}...\n")
    
    # Show conversation stats
    print("📊 Conversation Statistics:")
    print("-" * 30)
    stats = architect.get_conversation_stats()
    print(f"Total messages: {stats['total_messages']}")
    print(f"Active tasks: {stats['active_tasks']}")
    print(f"Current phase: {stats['current_phase']}")
    print(f"Communities: {stats['communities']}")
    
    # Example 4: Creating a checkpoint
    print("\nExample 4: Creating checkpoints")
    print("-" * 30)
    
    checkpoint_id = await architect.create_checkpoint(
        title="Authentication Design Complete",
        checkpoint_type="decision"
    )
    print(f"✅ Created checkpoint: {checkpoint_id[:8]}...")
    
    # Example 5: Switching context modes
    print("\nExample 5: Context compression modes")
    print("-" * 30)
    
    # Switch to aggressive mode for very long conversations
    architect.switch_context_mode("aggressive")
    print("Switched to AGGRESSIVE mode - maximum compression")
    
    # Add many messages to see compression in action
    for i in range(5):
        await architect.process_message(
            f"Let's discuss implementation detail {i+1}",
            task_ids=["IMPL-001"]
        )
    
    stats = architect.get_conversation_stats()
    print(f"\nAfter {stats['total_messages']} messages:")
    print(f"- Summarized: {stats['summarized_nodes']} nodes")
    print(f"- Compression: {stats.get('compression_ratio', 0):.1%}")
    
    # Example 6: Saving and loading state
    print("\nExample 6: Persistence")
    print("-" * 30)
    
    # Save current conversation
    state_file = await architect.save_conversation_state()
    print(f"✅ Saved conversation to: {state_file}")
    
    # Create new architect and restore
    new_architect = create_context_aware_architect(
        project_path="./my_project",
        mode="balanced"
    )
    
    if await new_architect.load_conversation_state():
        print(f"✅ Restored {len(new_architect.context_graph.nodes)} messages")
    
    print("\n" + "="*50)
    print("✅ Example complete!")


if __name__ == "__main__":
    # Set mock mode if no API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  No OPENAI_API_KEY found, using mock mode\n")
        os.environ["OPENAI_API_KEY"] = "mock-key"
    
    asyncio.run(main())