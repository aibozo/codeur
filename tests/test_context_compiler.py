#!/usr/bin/env python3
"""
Tests for the context compilation system.
"""

import asyncio
import pytest
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_graph import ContextGraph
from src.architect.context_graph_models import (
    ResolutionConfig, ResolutionLevel, ConversationPhase
)
from src.architect.context_compiler import (
    ContextCompiler, DistanceBasedStrategy, ImportanceBasedStrategy,
    TokenBudgetStrategy
)


@pytest.mark.asyncio
async def test_basic_compilation():
    """Test basic context compilation."""
    # Create graph with some messages
    config = ResolutionConfig(
        full_context_distance=2,
        summary_distance=4,
        title_distance=6
    )
    graph = ContextGraph("test_project", config)
    
    # Build a conversation
    messages = [
        ("user", "Hello, I need help with my project"),
        ("assistant", "I'd be happy to help! What are you working on?"),
        ("user", "I'm building a web API"),
        ("assistant", "Great! What framework are you using?"),
        ("user", "FastAPI"),
        ("assistant", "Excellent choice! FastAPI is great for building APIs."),
        ("user", "How should I structure it?"),
        ("assistant", "Here's a recommended structure..."),
    ]
    
    parent_id = None
    nodes = []
    for role, content in messages:
        node = await graph.add_message(role, content, parent_id=parent_id)
        nodes.append(node)
        parent_id = node.id
        
    # Create compiler
    compiler = ContextCompiler(graph)
    
    # Compile from the last message
    window = await compiler.compile_context(nodes[-1].id)
    
    # Check resolutions
    assert window.current_node_id == nodes[-1].id
    assert len(window.nodes) == len(messages)
    
    # Verify distance-based resolutions
    for i, node in enumerate(nodes):
        resolution = window.resolution_map[node.id]
        distance = len(nodes) - 1 - i
        
        if distance <= 2:
            assert resolution == ResolutionLevel.FULL
        elif distance <= 4:
            assert resolution == ResolutionLevel.SUMMARY
        elif distance <= 6:
            assert resolution == ResolutionLevel.TITLE
        else:
            assert resolution == ResolutionLevel.HIDDEN


@pytest.mark.asyncio
async def test_importance_preservation():
    """Test that important nodes get better resolution."""
    config = ResolutionConfig(
        full_context_distance=1,
        importance_threshold=0.8
    )
    graph = ContextGraph("test_project", config)
    compiler = ContextCompiler(graph)
    
    # Add messages with varying importance
    nodes = []
    parent_id = None
    
    # Regular messages
    for i in range(3):
        node = await graph.add_message(
            "user", f"Regular message {i}", 
            parent_id=parent_id,
            importance=0.5
        )
        nodes.append(node)
        parent_id = node.id
        
    # Important decision
    important = await graph.add_message(
        "assistant", 
        "DECISION: We will use PostgreSQL for the database",
        parent_id=parent_id,
        importance=0.9
    )
    nodes.append(important)
    parent_id = important.id
    
    # More regular messages
    for i in range(3):
        node = await graph.add_message(
            "user", f"Follow-up {i}",
            parent_id=parent_id,
            importance=0.5
        )
        nodes.append(node)
        parent_id = node.id
        
    # Compile from the end
    window = await compiler.compile_context(nodes[-1].id)
    
    # Check that important node has better resolution
    important_resolution = window.resolution_map[important.id]
    
    # Important node should be at least summary despite distance
    assert important_resolution in [ResolutionLevel.FULL, ResolutionLevel.SUMMARY]


@pytest.mark.asyncio
async def test_token_budget():
    """Test compilation with token budget constraints."""
    graph = ContextGraph("test_project")
    compiler = ContextCompiler(graph)
    
    # Add messages with known token counts
    nodes = []
    parent_id = None
    
    for i in range(10):
        # Create content with predictable token count
        content = "word " * 20  # ~20 tokens
        node = await graph.add_message("user", content, parent_id=parent_id)
        node.token_count = 20  # Override for predictable testing
        nodes.append(node)
        parent_id = node.id
        
    # Compile with limited token budget
    window = await compiler.compile_context(
        nodes[-1].id,
        max_tokens=100  # Only room for ~5 full messages
    )
    
    # Should have limited full nodes due to budget
    assert window.full_nodes <= 5
    assert window.total_tokens <= 100


@pytest.mark.asyncio
async def test_branch_compilation():
    """Test compiling only the current branch."""
    graph = ContextGraph("test_project")
    compiler = ContextCompiler(graph)
    
    # Create a branching conversation
    root = await graph.add_message("user", "Initial question")
    resp = await graph.add_message("assistant", "Initial response")
    
    # Branch 1
    branch1_1 = await graph.add_message("user", "Branch 1 question", parent_id=resp.id)
    branch1_2 = await graph.add_message("assistant", "Branch 1 response", parent_id=branch1_1.id)
    
    # Branch 2
    branch2_1 = await graph.add_message("user", "Branch 2 question", parent_id=resp.id)
    branch2_2 = await graph.add_message("assistant", "Branch 2 response", parent_id=branch2_1.id)
    
    # Compile branch 1 only
    window = await compiler.compile_context(
        branch1_2.id,
        include_branch_only=True
    )
    
    # Should only include branch 1 nodes
    node_ids = {n.id for n in window.nodes}
    assert root.id in node_ids
    assert resp.id in node_ids
    assert branch1_1.id in node_ids
    assert branch1_2.id in node_ids
    
    # Should not include branch 2
    assert branch2_1.id not in node_ids
    assert branch2_2.id not in node_ids


@pytest.mark.asyncio
async def test_formatted_output():
    """Test the formatted context output."""
    graph = ContextGraph("test_project")
    
    # Add some messages
    msg1 = await graph.add_message("user", "What database should I use?")
    msg2 = await graph.add_message("assistant", "I recommend PostgreSQL for your use case")
    msg3 = await graph.add_message("user", "How do I set it up?")
    
    # Add summaries to first messages
    msg1.summary = "User asks about database choice"
    msg1.summary_token_count = 6
    
    # Compile context
    compiler = ContextCompiler(graph)
    window = await compiler.compile_context(msg3.id)
    
    # Get formatted output
    formatted = window.get_formatted_context()
    
    assert "user:" in formatted
    assert "assistant:" in formatted
    assert len(formatted) > 0


async def demo_context_compilation():
    """Demonstrate context compilation with different strategies."""
    print("\nContext Compilation Demo")
    print("=" * 50)
    
    # Create graph with configuration
    config = ResolutionConfig(
        full_context_distance=3,
        summary_distance=6,
        title_distance=10,
        target_context_size=500,
        importance_threshold=0.8
    )
    graph = ContextGraph("demo_project", config)
    print("✓ Created context graph")
    
    # Build a longer conversation
    conversation = [
        ("user", "I want to build a task management system", 0.7),
        ("assistant", "I'll help you build a task management system. What features do you need?", 0.5),
        ("user", "User authentication, task CRUD, and notifications", 0.6),
        ("assistant", "Let's start with authentication. We'll use JWT tokens.", 0.5),
        ("user", "Should we use a library or implement from scratch?", 0.5),
        ("assistant", "DECISION: Use FastAPI-Users library for authentication", 0.9),  # Important
        ("user", "Great! What about the database?", 0.5),
        ("assistant", "DECISION: PostgreSQL with SQLAlchemy ORM", 0.9),  # Important
        ("user", "How should we structure the project?", 0.6),
        ("assistant", "Here's my recommended structure:\n- src/\n  - api/\n  - models/\n  - services/", 0.7),
        ("user", "Let's implement the user model first", 0.5),
        ("assistant", "Here's the user model implementation...", 0.6),
        ("user", "Now let's add the task model", 0.5),
        ("assistant", "Here's the task model with relationships...", 0.6),
        ("user", "Can we add due dates and priorities?", 0.5),
        ("assistant", "Yes, I'll update the model with those fields", 0.6),
    ]
    
    # Add messages
    parent_id = None
    nodes = []
    for role, content, importance in conversation:
        node = await graph.add_message(
            role, content, 
            parent_id=parent_id,
            importance=importance
        )
        nodes.append(node)
        parent_id = node.id
        print(f"✓ Added: {role} - {content[:40]}...")
        
    print(f"\n📊 Total messages: {len(nodes)}")
    
    # Create compiler
    compiler = ContextCompiler(graph)
    
    # 1. Standard compilation
    print("\n📝 Standard Context Compilation:")
    window = await compiler.compile_context(nodes[-1].id)
    
    print(f"  Total tokens: {window.total_tokens}")
    print(f"  Full nodes: {window.full_nodes}")
    print(f"  Summary nodes: {window.summary_nodes}")
    print(f"  Title nodes: {window.title_nodes}")
    print(f"  Hidden nodes: {window.hidden_nodes}")
    
    # Show resolution for each message
    print("\n  Resolution map:")
    for i, node in enumerate(nodes):
        resolution = window.resolution_map.get(node.id, ResolutionLevel.HIDDEN)
        distance = len(nodes) - 1 - i
        print(f"    [{i}] Distance {distance}: {resolution.value} - {node.content[:30]}...")
        
    # 2. Token-constrained compilation
    print("\n💰 Token-Constrained Compilation (max 200 tokens):")
    constrained_window = await compiler.compile_context(
        nodes[-1].id,
        max_tokens=200
    )
    
    print(f"  Total tokens: {constrained_window.total_tokens}")
    print(f"  Full nodes: {constrained_window.full_nodes}")
    print(f"  Summary nodes: {constrained_window.summary_nodes}")
    
    # 3. Branch-only compilation
    print("\n🌳 Branch-Only Compilation:")
    branch_window = await compiler.compile_context(
        nodes[-1].id,
        include_branch_only=True
    )
    
    print(f"  Nodes included: {len(branch_window.nodes)}")
    print(f"  Total tokens: {branch_window.total_tokens}")
    
    # 4. Focus compilation
    print("\n🎯 Focused Compilation (on decisions):")
    # Find decision nodes
    decision_nodes = [n for n in nodes if "DECISION:" in n.content]
    decision_ids = [n.id for n in decision_nodes]
    
    focus_window = await compiler.compile_with_focus(
        nodes[-1].id,
        focus_node_ids=decision_ids
    )
    
    print(f"  Decision nodes found: {len(decision_nodes)}")
    for node in decision_nodes:
        resolution = focus_window.resolution_map[node.id]
        print(f"    {resolution.value}: {node.content[:50]}...")
        
    # 5. Context size estimates
    print("\n📏 Context Size Estimates:")
    estimates = compiler.estimate_context_size(nodes[-1].id)
    for strategy, tokens in estimates.items():
        print(f"  {strategy}: {tokens} tokens")
        
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_context_compilation())
    
    # Run tests
    print("\nRunning tests...")
    pytest.main([__file__, "-v"])