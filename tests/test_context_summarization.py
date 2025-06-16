#!/usr/bin/env python3
"""
Tests for the context summarization system.
"""

import asyncio
import pytest
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_graph import ContextGraph
from src.architect.context_graph_models import ResolutionConfig, ConversationPhase
from src.architect.context_summarizer import ContextSummarizer
from src.core.summarizer import SummarizationService


@pytest.mark.asyncio
async def test_summarization_service():
    """Test basic summarization service functionality."""
    # Create service without LLM (will use mock)
    service = SummarizationService(llm_client=None, model="gpt-4o-mini")
    
    # Test single summarization
    content = "This is a long conversation about implementing authentication in a web application. We discussed JWT tokens, refresh tokens, and session management. The user wants to implement a secure system."
    
    result = await service.summarize(
        content,
        max_tokens=50,
        preserve_decisions=True
    )
    
    assert result.summary.startswith("[Summary]")  # Mock prefix
    assert result.token_count > 0
    assert result.quality_score > 0
    assert result.cost == 0  # Mock has no cost
    
    # Test batch summarization
    contents = [
        "First message about database design",
        "Second message about API endpoints",
        "Third message about frontend implementation"
    ]
    
    results = await service.summarize_batch(contents, max_tokens=30)
    assert len(results) == 3
    assert all(r.summary for r in results)
    
    # Test caching
    result2 = await service.summarize(content, max_tokens=50)
    assert service.metrics.cache_hits == 1
    
    # Check metrics
    metrics = service.get_metrics_summary()
    assert metrics["total_requests"] > 0
    assert metrics["cache_hit_rate"] > 0


@pytest.mark.asyncio
async def test_context_summarizer():
    """Test context-aware summarization."""
    # Create graph with config
    config = ResolutionConfig(
        full_context_distance=2,  # Small for testing
        summary_distance=5,
        max_summary_tokens=50,
        summarization_delay_seconds=0  # No delay for testing
    )
    graph = ContextGraph("test_project", config)
    
    # Create summarization service
    service = SummarizationService(llm_client=None)
    summarizer = ContextSummarizer(graph, service)
    
    # Build a conversation
    messages = [
        ("user", "I need to build an authentication system"),
        ("assistant", "I'll help you build an authentication system. What framework are you using?"),
        ("user", "I'm using FastAPI with PostgreSQL"),
        ("assistant", "Great! For FastAPI with PostgreSQL, I recommend using JWT tokens..."),
        ("user", "How do I handle refresh tokens?"),
        ("assistant", "Refresh tokens should be stored securely..."),
        ("user", "What about password hashing?"),
        ("assistant", "Use bcrypt for password hashing...")
    ]
    
    # Add messages to graph
    parent_id = None
    for role, content in messages:
        node = await graph.add_message(role, content, parent_id=parent_id)
        parent_id = node.id
        
    # Move current position back to trigger summarization
    graph.current_node_id = list(graph.nodes.keys())[2]  # Third message
    
    # Run summarization
    result = await summarizer.summarize_old_nodes(force=True)
    
    assert result["processed"] > 0
    assert result["successful"] > 0
    
    # Check that some nodes now have summaries
    summarized_count = sum(1 for n in graph.nodes.values() if n.summary)
    assert summarized_count > 0
    
    # Get stats
    stats = summarizer.get_summarization_stats()
    assert stats["summarized_nodes"] > 0
    assert stats["compression_ratio"] > 0


@pytest.mark.asyncio
async def test_community_summarization():
    """Test summarizing communities."""
    graph = ContextGraph("test_project")
    service = SummarizationService(llm_client=None)
    summarizer = ContextSummarizer(graph, service)
    
    # Create messages about a specific topic
    auth_messages = []
    parent_id = None
    
    for role, content in [
        ("user", "How do I implement JWT authentication?"),
        ("assistant", "JWT authentication involves..."),
        ("user", "What about token expiration?"),
        ("assistant", "Token expiration is important for security...")
    ]:
        node = await graph.add_message(role, content, parent_id=parent_id)
        auth_messages.append(node)
        parent_id = node.id
        
    # Create community
    community = graph.create_community(
        "JWT Authentication",
        "authentication",
        {n.id for n in auth_messages}
    )
    
    # Summarize community
    summary = await summarizer.summarize_community(community.id)
    
    assert summary is not None
    assert len(summary) > 0
    assert community.summary == summary


@pytest.mark.asyncio
async def test_importance_preservation():
    """Test that important messages are preserved longer."""
    config = ResolutionConfig(
        full_context_distance=1,
        importance_threshold=0.8
    )
    graph = ContextGraph("test_project", config)
    service = SummarizationService(llm_client=None)
    summarizer = ContextSummarizer(graph, service)
    
    # Add regular message
    regular = await graph.add_message(
        "user", 
        "What's the weather today?",
        importance=0.3
    )
    
    # Add important decision
    important = await graph.add_message(
        "assistant",
        "We've decided to use PostgreSQL as our primary database",
        importance=0.9
    )
    
    # Add more messages to increase distance
    for i in range(5):
        await graph.add_message("user", f"Message {i}")
        
    # Run summarization
    result = await summarizer.summarize_old_nodes(force=True)
    
    # Check that regular message was summarized but important wasn't
    regular_node = graph.get_node(regular.id)
    important_node = graph.get_node(important.id)
    
    assert regular_node.summary is not None  # Should be summarized
    assert important_node.summary is None  # Should be preserved


@pytest.mark.asyncio
async def test_cost_estimation():
    """Test cost estimation for summarization."""
    service = SummarizationService(llm_client=None)
    
    # Estimate cost for 100 nodes
    cost = await service.estimate_cost_for_nodes(
        node_count=100,
        avg_content_length=500,  # 500 chars average
        max_tokens=50
    )
    
    # With GPT-4o-mini pricing:
    # Input: 100 * 125 tokens = 12,500 tokens = $0.001875
    # Output: 100 * 50 tokens = 5,000 tokens = $0.003
    # Total: ~$0.0049
    
    assert cost > 0
    assert cost < 0.01  # Should be less than 1 cent


async def demo_summarization_flow():
    """Demonstrate the summarization flow."""
    print("\nContext Summarization Demo")
    print("=" * 50)
    
    # Create components
    config = ResolutionConfig(
        full_context_distance=2,
        summary_distance=4,
        max_summary_tokens=40
    )
    graph = ContextGraph("demo_project", config)
    service = SummarizationService(llm_client=None)
    summarizer = ContextSummarizer(graph, service)
    
    print("✓ Created context graph with aggressive summarization")
    
    # Simulate a conversation
    conversation = [
        ("user", "I need help building a REST API for a todo application."),
        ("assistant", "I'll help you build a REST API for a todo app. What language/framework would you like to use?"),
        ("user", "I want to use Python with FastAPI."),
        ("assistant", "Great choice! FastAPI is excellent for building REST APIs. Let's start by setting up the project structure."),
        ("user", "Should I use SQLAlchemy or raw SQL?"),
        ("assistant", "I recommend SQLAlchemy as it provides an ORM that works well with FastAPI and makes database operations easier."),
        ("user", "How do I structure the project?"),
        ("assistant", "Here's a recommended project structure for a FastAPI todo app...")
    ]
    
    # Add messages
    parent_id = None
    for i, (role, content) in enumerate(conversation):
        node = await graph.add_message(role, content, parent_id=parent_id)
        parent_id = node.id
        print(f"✓ Added message {i+1}: {role}")
        
    # Move current position to middle of conversation to trigger summarization
    # This makes earlier messages "far away" in the graph
    all_node_ids = list(graph.nodes.keys())
    graph.current_node_id = all_node_ids[4]  # Move to 5th message
    
    # Run summarization
    print("\n📝 Running summarization...")
    result = await summarizer.summarize_old_nodes(force=True)
    
    print(f"✓ Processed {result['processed']} nodes")
    if 'total_cost' in result:
        print(f"✓ Cost: ${result['total_cost']:.4f}")
    else:
        print(f"✓ Result: {result}")
    
    # Show what got summarized
    print("\n📊 Summarization results:")
    for node_id, node in graph.nodes.items():
        distance = graph.calculate_distance(graph.current_node_id, node_id)
        if node.summary:
            print(f"\nNode {node_id[:8]} (distance {distance}):")
            print(f"  Original ({node.token_count} tokens): {node.content[:50]}...")
            print(f"  Summary ({node.summary_token_count} tokens): {node.summary[:80]}...")
            
    # Show stats
    stats = summarizer.get_summarization_stats()
    print(f"\n📈 Overall stats:")
    print(f"  Compression ratio: {stats['compression_ratio']:.1%}")
    print(f"  Summarized: {stats['summarized_nodes']}/{stats['total_nodes']} nodes")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_summarization_flow())
    
    # Run tests
    print("\nRunning tests...")
    pytest.main([__file__, "-v"])