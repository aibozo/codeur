#!/usr/bin/env python3
"""
Test and demonstrate task-based community integration.
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_graph import ContextGraph
from src.architect.context_graph_models import ResolutionConfig, ConversationPhase
from src.architect.context_summarizer import ContextSummarizer
from src.core.summarizer import SummarizationService


async def demo_task_community_integration():
    """Demonstrate automatic task-based community creation."""
    
    print("\n" + "="*60)
    print("TASK-BASED COMMUNITY INTEGRATION DEMO")
    print("="*60)
    
    # Create context graph
    config = ResolutionConfig()
    graph = ContextGraph("project_with_tasks", config)
    
    # Create summarizer for communities
    summarizer_service = SummarizationService(llm_client=None)
    context_summarizer = ContextSummarizer(graph, summarizer_service)
    
    print("\n📋 Simulating task-driven conversation...")
    
    # Simulate messages for different tasks
    conversations = [
        # Task 1: Authentication
        {
            "task_ids": ["AUTH-001"],
            "messages": [
                ("user", "Let's implement user authentication"),
                ("assistant", "I'll help you set up JWT-based authentication"),
                ("user", "Should we use OAuth2?"),
                ("assistant", "Yes, OAuth2 with JWT tokens is a great choice"),
                ("user", "What about password hashing?"),
                ("assistant", "Use bcrypt with a cost factor of 12"),
            ]
        },
        
        # Task 2: Database Design
        {
            "task_ids": ["DB-001"],
            "messages": [
                ("user", "Now let's design the database schema"),
                ("assistant", "Starting with user and authentication tables"),
                ("user", "Should we add audit fields?"),
                ("assistant", "Yes, created_at, updated_at, and deleted_at"),
            ]
        },
        
        # Task 3: API Endpoints (relates to both tasks)
        {
            "task_ids": ["API-001", "AUTH-001", "DB-001"],
            "messages": [
                ("user", "Let's create the API endpoints"),
                ("assistant", "We'll need login, register, and profile endpoints"),
                ("user", "Don't forget password reset"),
                ("assistant", "Good point, adding password reset flow"),
            ]
        },
        
        # Back to auth task
        {
            "task_ids": ["AUTH-001"],
            "messages": [
                ("user", "How do we handle refresh tokens?"),
                ("assistant", "Store refresh tokens in a separate table with expiry"),
            ]
        }
    ]
    
    # Add all messages
    parent_id = None
    total_messages = 0
    
    for conv_group in conversations:
        task_ids = conv_group["task_ids"]
        print(f"\n  Working on tasks: {', '.join(task_ids)}")
        
        for role, content in conv_group["messages"]:
            node = await graph.add_message(
                role=role,
                content=content,
                parent_id=parent_id,
                task_ids=task_ids,
                phase=ConversationPhase.IMPLEMENTATION
            )
            parent_id = node.id
            total_messages += 1
            print(f"    + {role}: {content[:40]}...")
    
    print(f"\n✅ Added {total_messages} messages")
    
    # Show automatic task communities
    print("\n🏘️ Automatic Task Communities:")
    task_communities = [c for c in graph.communities.values() if c.task_id]
    
    for community in task_communities:
        print(f"\n  Community: {community.name}")
        print(f"  Task ID: {community.task_id}")
        print(f"  Messages: {len(community.node_ids)}")
        
        # Get task messages
        task_messages = graph.get_task_messages(community.task_id)
        print(f"  Message preview:")
        for msg in task_messages[:3]:
            print(f"    - {msg.role}: {msg.content[:50]}...")
            
        # Generate community summary
        summary = await context_summarizer.summarize_community(community.id)
        if summary:
            print(f"  Summary: {summary[:100]}...")
    
    # Show cross-task relationships
    print("\n🔗 Cross-Task Relationships:")
    for node in graph.nodes.values():
        if len(node.related_task_ids) > 1 or (node.primary_task_id and node.related_task_ids):
            all_tasks = [node.primary_task_id] + node.related_task_ids if node.primary_task_id else node.related_task_ids
            print(f"  Message '{node.content[:40]}...' relates to: {', '.join(all_tasks)}")
    
    # Demonstrate task-specific context compilation
    print("\n📚 Task-Specific Context Retrieval:")
    
    # Get all messages for AUTH-001
    auth_community = graph.get_task_community("AUTH-001")
    if auth_community:
        print(f"\n  Task AUTH-001 context:")
        print(f"  Total messages: {len(auth_community.node_ids)}")
        
        # Get messages in order
        auth_messages = graph.get_task_messages("AUTH-001")
        print(f"  Conversation flow:")
        for msg in auth_messages:
            print(f"    [{msg.timestamp.strftime('%H:%M:%S')}] {msg.role}: {msg.content[:60]}...")
    
    # Show how this integrates with context compilation
    print("\n🔧 Integration with Context Compiler:")
    print("""
    # When compiling context, task communities can be included:
    
    compiler = ContextCompiler(graph)
    
    # Include all communities for current task
    if current_task_id:
        window = await compiler.compile_context(
            current_node_id,
            include_communities=True  # Will include task communities
        )
        
    # Or focus on specific task's messages
    task_messages = graph.get_task_messages(current_task_id)
    task_node_ids = [msg.id for msg in task_messages]
    
    window = await compiler.compile_with_focus(
        current_node_id,
        focus_node_ids=task_node_ids
    )
    """)
    
    print("\n✨ Benefits of Task-Based Communities:")
    print("  1. Automatic grouping of related discussions")
    print("  2. Easy retrieval of all context for a specific task")
    print("  3. Task-specific summaries for quick understanding")
    print("  4. Cross-task relationship tracking")
    print("  5. Integration with existing task graph system")
    
    return graph


async def test_task_community_features():
    """Test specific task community features."""
    print("\n\n🧪 Testing Task Community Features...")
    
    graph = ContextGraph("test_project")
    
    # Test 1: Single task assignment
    msg1 = await graph.add_message(
        "user", 
        "Implement login endpoint",
        task_ids=["TASK-001"]
    )
    
    # Check community was created
    community = graph.get_task_community("TASK-001")
    assert community is not None
    assert community.task_id == "TASK-001"
    assert msg1.id in community.node_ids
    print("  ✓ Single task community creation")
    
    # Test 2: Multiple task assignment
    msg2 = await graph.add_message(
        "assistant",
        "Login endpoint needs database and auth setup",
        task_ids=["TASK-001", "TASK-002", "TASK-003"]
    )
    
    # Check all communities were updated
    for task_id in ["TASK-001", "TASK-002", "TASK-003"]:
        community = graph.get_task_community(task_id)
        assert community is not None
        assert msg2.id in community.node_ids
    print("  ✓ Multiple task community updates")
    
    # Test 3: Task message retrieval
    task_messages = graph.get_task_messages("TASK-001")
    assert len(task_messages) == 2
    assert all(msg.id in [msg1.id, msg2.id] for msg in task_messages)
    print("  ✓ Task message retrieval")
    
    # Test 4: Primary vs related tasks
    assert msg2.primary_task_id == "TASK-001"  # First task is primary
    assert "TASK-002" in msg2.related_task_ids
    assert "TASK-003" in msg2.related_task_ids
    print("  ✓ Primary and related task tracking")
    
    print("\n✅ All task community features working correctly!")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_task_community_integration())
    
    # Run tests
    asyncio.run(test_task_community_features())