#!/usr/bin/env python3
"""
Tests for the Context Graph system.
"""

import asyncio
import pytest
from datetime import datetime
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_graph import ContextGraph
from src.architect.context_graph_models import (
    MessageNode, ResolutionConfig, ConversationPhase,
    MessageCommunity, AGGRESSIVE_COMPRESSION, CONTEXT_RICH
)


class TestContextGraph:
    """Test suite for ContextGraph functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_graph_operations(self):
        """Test basic graph construction and navigation."""
        graph = ContextGraph("test_project")
        
        # Add root message
        root = await graph.add_message(
            role="user",
            content="Hello, I need help with authentication"
        )
        assert root.parent_id is None
        assert root.id in graph.root_nodes
        assert graph.current_node_id == root.id
        
        # Add response
        response = await graph.add_message(
            role="assistant",
            content="I'll help you with authentication. What framework are you using?"
        )
        assert response.parent_id == root.id
        assert root.id in graph.nodes[response.id].parent_id
        
        # Add follow-up
        followup = await graph.add_message(
            role="user",
            content="I'm using FastAPI"
        )
        assert followup.parent_id == response.id
        
        # Test traversal
        ancestors = graph.get_ancestors(followup.id)
        assert len(ancestors) == 2
        assert ancestors[0].id == root.id
        assert ancestors[1].id == response.id
        
        # Test conversation path
        path = graph.get_conversation_path(followup.id)
        assert len(path) == 3
        assert path[0].id == root.id
        assert path[2].id == followup.id
        
    @pytest.mark.asyncio
    async def test_distance_calculation(self):
        """Test distance calculation between nodes."""
        graph = ContextGraph("test_project")
        
        # Create a simple conversation tree
        root = await graph.add_message("user", "Start")
        child1 = await graph.add_message("assistant", "Response 1")
        child2 = await graph.add_message("user", "Question 2")
        
        # Create a branch
        branch = await graph.add_message("user", "Branch question", parent_id=child1.id)
        
        # Test distances
        assert graph.calculate_distance(root.id, root.id) == 0
        assert graph.calculate_distance(root.id, child1.id) == 1
        assert graph.calculate_distance(root.id, child2.id) == 2
        assert graph.calculate_distance(child2.id, branch.id) == 2
        assert graph.calculate_distance(branch.id, root.id) == 2
        
    @pytest.mark.asyncio
    async def test_branching_conversations(self):
        """Test handling of branching conversations."""
        graph = ContextGraph("test_project")
        
        # Create main conversation
        root = await graph.add_message("user", "Initial question")
        resp1 = await graph.add_message("assistant", "Initial response")
        
        # Create two branches from the same parent
        branch1 = await graph.add_message("user", "Follow-up A", parent_id=resp1.id)
        branch2 = await graph.add_message("user", "Follow-up B", parent_id=resp1.id)
        
        # Verify parent has both children
        parent_node = graph.get_node(resp1.id)
        assert len(parent_node.children_ids) == 2
        assert branch1.id in parent_node.children_ids
        assert branch2.id in parent_node.children_ids
        
        # Test common ancestor
        common = graph.find_nearest_common_ancestor(branch1.id, branch2.id)
        assert common == resp1.id
        
    @pytest.mark.asyncio
    async def test_communities(self):
        """Test community creation and management."""
        graph = ContextGraph("test_project")
        
        # Create messages about authentication
        auth_msgs = []
        parent_id = None
        for i, (role, content) in enumerate([
            ("user", "How do I implement JWT authentication?"),
            ("assistant", "Here's how to implement JWT..."),
            ("user", "What about refresh tokens?"),
            ("assistant", "Refresh tokens work like this...")
        ]):
            msg = await graph.add_message(role, content, parent_id=parent_id)
            auth_msgs.append(msg)
            parent_id = msg.id
            
        # Create authentication community
        community = graph.create_community(
            name="JWT Authentication Discussion",
            theme="authentication",
            node_ids={msg.id for msg in auth_msgs},
            task_id="auth_task_123"
        )
        
        assert len(community.node_ids) == 4
        assert community.task_id == "auth_task_123"
        
        # Verify nodes are marked with community
        for msg in auth_msgs:
            node = graph.get_node(msg.id)
            assert node.community_id == community.id
            
    @pytest.mark.asyncio
    async def test_task_association(self):
        """Test associating messages with tasks."""
        graph = ContextGraph("test_project")
        
        # Add messages with task associations
        msg1 = await graph.add_message(
            "user",
            "Implement user registration",
            task_ids=["task_001", "task_002"]
        )
        
        assert msg1.primary_task_id == "task_001"
        assert msg1.related_task_ids == ["task_002"]
        
    @pytest.mark.asyncio
    async def test_nodes_by_distance(self):
        """Test getting nodes grouped by distance."""
        graph = ContextGraph("test_project")
        
        # Create a conversation tree
        root = await graph.add_message("user", "Root")
        c1 = await graph.add_message("assistant", "Child 1")
        c2 = await graph.add_message("user", "Child 2")
        gc1 = await graph.add_message("assistant", "Grandchild 1")
        
        # Get nodes by distance from root
        nodes_by_dist = graph.get_nodes_by_distance(root.id, max_distance=3)
        
        assert len(nodes_by_dist[0]) == 1  # Root itself
        assert len(nodes_by_dist[1]) == 1  # Child 1
        assert len(nodes_by_dist[2]) == 1  # Child 2
        assert len(nodes_by_dist[3]) == 1  # Grandchild 1
        
    @pytest.mark.asyncio
    async def test_conversation_phases(self):
        """Test conversation phase tracking."""
        graph = ContextGraph("test_project")
        
        # Different phases of conversation
        explore = await graph.add_message(
            "user", 
            "What options do I have?",
            phase=ConversationPhase.EXPLORATION
        )
        
        plan = await graph.add_message(
            "assistant",
            "Here's the plan...",
            phase=ConversationPhase.PLANNING
        )
        
        impl = await graph.add_message(
            "user",
            "Let's implement it",
            phase=ConversationPhase.IMPLEMENTATION
        )
        
        assert explore.conversation_phase == ConversationPhase.EXPLORATION
        assert plan.conversation_phase == ConversationPhase.PLANNING
        assert impl.conversation_phase == ConversationPhase.IMPLEMENTATION
        
    @pytest.mark.asyncio
    async def test_importance_scoring(self):
        """Test importance score handling."""
        graph = ContextGraph("test_project")
        
        # Regular message
        regular = await graph.add_message(
            "user",
            "What's the weather?",
            importance=0.3
        )
        
        # Important decision
        important = await graph.add_message(
            "assistant",
            "We should use PostgreSQL for the database",
            importance=0.9
        )
        
        assert regular.importance_score == 0.3
        assert important.importance_score == 0.9
        
    @pytest.mark.asyncio
    async def test_serialization(self):
        """Test graph serialization and deserialization."""
        graph = ContextGraph("test_project")
        
        # Build a small graph
        root = await graph.add_message("user", "Hello")
        resp = await graph.add_message("assistant", "Hi there!")
        
        # Create a community
        community = graph.create_community(
            "Greeting",
            "greeting",
            {root.id, resp.id}
        )
        
        # Serialize
        data = graph.to_dict()
        
        # Deserialize
        graph2 = ContextGraph.from_dict(data)
        
        # Verify structure
        assert len(graph2.nodes) == 2
        assert len(graph2.communities) == 1
        assert graph2.current_node_id == resp.id
        
        # Verify relationships preserved
        root2 = graph2.get_node(root.id)
        assert resp.id in root2.children_ids
        
    @pytest.mark.asyncio
    async def test_configuration_modes(self):
        """Test different configuration modes."""
        # Aggressive compression mode
        aggressive_graph = ContextGraph("test1", AGGRESSIVE_COMPRESSION)
        assert aggressive_graph.config.full_context_distance == 3
        assert aggressive_graph.config.max_summary_tokens == 50
        
        # Context rich mode
        rich_graph = ContextGraph("test2", CONTEXT_RICH)
        assert rich_graph.config.full_context_distance == 10
        assert rich_graph.config.max_summary_tokens == 150
        
    @pytest.mark.asyncio
    async def test_access_tracking(self):
        """Test node access tracking."""
        graph = ContextGraph("test_project")
        
        msg = await graph.add_message("user", "Test message")
        initial_access = msg.access_count
        
        # Access the node
        node = graph.get_node(msg.id)
        assert node.access_count == initial_access + 1
        assert node.last_accessed is not None
        
        # Access again
        node2 = graph.get_node(msg.id)
        assert node2.access_count == initial_access + 2


@pytest.mark.asyncio
async def test_basic_functionality():
    """Quick test of basic functionality."""
    print("\nTesting Context Graph Basic Functionality")
    print("=" * 50)
    
    # Create graph
    graph = ContextGraph("demo_project")
    print("✓ Created context graph")
    
    # Add some messages
    msg1 = await graph.add_message("user", "Hello, I need help with my API")
    print(f"✓ Added user message: {msg1.id[:8]}")
    
    msg2 = await graph.add_message("assistant", "I'll help you with your API. What specifically do you need?")
    print(f"✓ Added assistant message: {msg2.id[:8]}")
    
    msg3 = await graph.add_message("user", "I need to add authentication")
    print(f"✓ Added follow-up message: {msg3.id[:8]}")
    
    # Test distance
    distance = graph.calculate_distance(msg1.id, msg3.id)
    print(f"✓ Distance from first to last message: {distance}")
    
    # Test path
    path = graph.get_conversation_path(msg3.id)
    print(f"✓ Conversation path length: {len(path)}")
    
    # Create community
    community = graph.create_community(
        "API Authentication",
        "authentication", 
        {msg1.id, msg2.id, msg3.id}
    )
    print(f"✓ Created community: {community.name}")
    
    # Test serialization
    data = graph.to_dict()
    print(f"✓ Serialized graph with {len(data['nodes'])} nodes")
    
    print("\n✅ All basic tests passed!")


if __name__ == "__main__":
    # Run basic functionality test
    asyncio.run(test_basic_functionality())
    
    # Run pytest
    print("\nRunning full test suite...")
    pytest.main([__file__, "-v"])