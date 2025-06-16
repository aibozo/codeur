#!/usr/bin/env python3
"""
Complete demonstration of the Context Graph system.

This shows how all components work together to manage long conversations efficiently.
"""

import asyncio
from datetime import datetime
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.context_graph import ContextGraph
from src.architect.context_graph_models import (
    ResolutionConfig, ResolutionLevel, ConversationPhase,
    AGGRESSIVE_COMPRESSION, BALANCED, CONTEXT_RICH
)
from src.architect.context_summarizer import ContextSummarizer
from src.core.summarizer import SummarizationService
from src.architect.context_compiler import ContextCompiler


async def simulate_long_conversation():
    """Simulate a realistic long conversation about building a web app."""
    
    print("\n" + "="*80)
    print("CONTEXT GRAPH SYSTEM - Complete Demo")
    print("="*80)
    
    # 1. Setup with aggressive compression for demo
    config = ResolutionConfig(
        full_context_distance=3,
        summary_distance=6,
        title_distance=10,
        max_summary_tokens=50,
        summarization_delay_seconds=0,  # No delay for demo
        daily_summarization_budget=1.0
    )
    
    print("\n📋 Configuration:")
    print(f"  Full context: {config.full_context_distance} messages")
    print(f"  Summaries: {config.summary_distance} messages")
    print(f"  Titles: {config.title_distance} messages")
    print(f"  Max summary tokens: {config.max_summary_tokens}")
    
    # 2. Create components
    graph = ContextGraph("webapp_project", config)
    summarizer_service = SummarizationService(llm_client=None)  # Mock mode
    context_summarizer = ContextSummarizer(graph, summarizer_service)
    compiler = ContextCompiler(graph)
    
    print("\n✅ System components initialized")
    
    # 3. Simulate a realistic conversation
    conversation_segments = [
        # Initial exploration
        [
            ("user", "I want to build a social media dashboard that aggregates data from multiple platforms", ConversationPhase.EXPLORATION, 0.7),
            ("assistant", "I'll help you build a social media dashboard. Which platforms do you want to integrate?", ConversationPhase.EXPLORATION, 0.5),
            ("user", "Twitter, LinkedIn, and Instagram to start with", ConversationPhase.EXPLORATION, 0.6),
            ("assistant", "Great choices. We'll need to use their respective APIs. Let's start with the architecture.", ConversationPhase.PLANNING, 0.6),
        ],
        
        # Architecture planning
        [
            ("user", "What's the best architecture for this?", ConversationPhase.PLANNING, 0.6),
            ("assistant", "DECISION: Microservices architecture with separate services for each platform", ConversationPhase.PLANNING, 0.9),
            ("user", "Should we use REST or GraphQL?", ConversationPhase.PLANNING, 0.7),
            ("assistant", "DECISION: GraphQL for the main API, REST for platform integrations", ConversationPhase.PLANNING, 0.9),
        ],
        
        # Technology decisions
        [
            ("user", "What tech stack should we use?", ConversationPhase.PLANNING, 0.7),
            ("assistant", "For the backend, I recommend Python with FastAPI for the services", ConversationPhase.PLANNING, 0.7),
            ("user", "And for the frontend?", ConversationPhase.PLANNING, 0.6),
            ("assistant", "DECISION: React with TypeScript and Tailwind CSS for the dashboard UI", ConversationPhase.PLANNING, 0.9),
        ],
        
        # Database design
        [
            ("user", "How should we structure the database?", ConversationPhase.PLANNING, 0.7),
            ("assistant", "We'll need separate schemas for each platform's data, plus a unified analytics schema", ConversationPhase.PLANNING, 0.8),
            ("user", "Which database should we use?", ConversationPhase.PLANNING, 0.7),
            ("assistant", "DECISION: PostgreSQL for structured data, Redis for caching API responses", ConversationPhase.PLANNING, 0.9),
        ],
        
        # Implementation details
        [
            ("user", "Let's start implementing the Twitter integration", ConversationPhase.IMPLEMENTATION, 0.6),
            ("assistant", "First, we'll need to set up Twitter API v2 authentication", ConversationPhase.IMPLEMENTATION, 0.6),
            ("user", "I have the API keys ready", ConversationPhase.IMPLEMENTATION, 0.5),
            ("assistant", "Great! Here's the basic Twitter service structure...", ConversationPhase.IMPLEMENTATION, 0.7),
        ],
        
        # More implementation
        [
            ("user", "How do we handle rate limiting?", ConversationPhase.IMPLEMENTATION, 0.7),
            ("assistant", "We'll implement exponential backoff and queue requests", ConversationPhase.IMPLEMENTATION, 0.7),
            ("user", "Can you show me the code?", ConversationPhase.IMPLEMENTATION, 0.5),
            ("assistant", "Here's the rate limiter implementation with Redis...", ConversationPhase.IMPLEMENTATION, 0.7),
        ]
    ]
    
    # 4. Add messages and periodically summarize
    print("\n💬 Building conversation...")
    all_nodes = []
    parent_id = None
    
    for segment_idx, segment in enumerate(conversation_segments):
        print(f"\n  Segment {segment_idx + 1}: ", end="")
        
        for role, content, phase, importance in segment:
            node = await graph.add_message(
                role=role,
                content=content,
                parent_id=parent_id,
                phase=phase,
                importance=importance
            )
            all_nodes.append(node)
            parent_id = node.id
            print(".", end="", flush=True)
            
        # Simulate moving forward in conversation
        # This triggers summarization of older messages
        if segment_idx > 1:
            await context_summarizer.summarize_old_nodes(force=True)
            
    print(f"\n\n📊 Conversation stats:")
    print(f"  Total messages: {len(all_nodes)}")
    print(f"  Current position: Message {len(all_nodes)}")
    
    # 5. Get summarization stats
    summary_stats = context_summarizer.get_summarization_stats()
    print(f"\n📝 Summarization stats:")
    print(f"  Summarized: {summary_stats['summarized_nodes']} messages")
    print(f"  Compression: {summary_stats['compression_ratio']:.1%}")
    print(f"  Original tokens: {summary_stats['total_original_tokens']}")
    print(f"  Summary tokens: {summary_stats['total_summary_tokens']}")
    
    # 6. Create communities for important topics
    print("\n🏘️ Creating communities...")
    
    # Find architecture decision nodes
    architecture_nodes = [n for n in all_nodes if "architecture" in n.content.lower() or "DECISION:" in n.content]
    if architecture_nodes:
        arch_community = graph.create_community(
            name="Architecture Decisions",
            theme="architecture",
            node_ids={n.id for n in architecture_nodes}
        )
        # Generate community summary
        await context_summarizer.summarize_community(arch_community.id)
        print(f"  ✓ Created 'Architecture Decisions' community with {len(architecture_nodes)} messages")
    
    # Find implementation nodes
    impl_nodes = [n for n in all_nodes if n.conversation_phase == ConversationPhase.IMPLEMENTATION]
    if impl_nodes:
        impl_community = graph.create_community(
            name="Implementation Details",
            theme="implementation",
            node_ids={n.id for n in impl_nodes}
        )
        await context_summarizer.summarize_community(impl_community.id)
        print(f"  ✓ Created 'Implementation Details' community with {len(impl_nodes)} messages")
    
    # 7. Compile context from current position
    print("\n🔧 Compiling context from current position...")
    
    # Standard compilation
    standard_window = await compiler.compile_context(all_nodes[-1].id)
    
    print(f"\n  Standard compilation:")
    print(f"    Total tokens: {standard_window.total_tokens}")
    print(f"    Full: {standard_window.full_nodes}")
    print(f"    Summary: {standard_window.summary_nodes}")
    print(f"    Title: {standard_window.title_nodes}")
    print(f"    Hidden: {standard_window.hidden_nodes}")
    print(f"    Communities included: {len(standard_window.communities)}")
    
    # Show what's in the context
    print("\n  📄 Context preview:")
    context_text = standard_window.get_formatted_context()
    lines = context_text.split('\n')
    for line in lines[:10]:  # First 10 lines
        if line.strip():
            print(f"    {line[:80]}...")
    print(f"    ... ({len(lines)} total lines)")
    
    # 8. Demonstrate focused compilation on decisions
    print("\n🎯 Focused compilation on decisions:")
    decision_nodes = [n for n in all_nodes if "DECISION:" in n.content]
    if decision_nodes:
        focused_window = await compiler.compile_with_focus(
            all_nodes[-1].id,
            focus_node_ids=[n.id for n in decision_nodes]
        )
        print(f"  Decisions preserved in full: {sum(1 for n in decision_nodes if focused_window.resolution_map[n.id] == ResolutionLevel.FULL)}")
    
    # 9. Show cost estimation
    print("\n💰 Cost estimation:")
    estimated_cost = await summarizer_service.estimate_cost_for_nodes(
        summary_stats['summarized_nodes'],
        avg_content_length=100,
        max_tokens=config.max_summary_tokens
    )
    print(f"  Estimated cost for {summary_stats['summarized_nodes']} summaries: ${estimated_cost:.4f}")
    print(f"  Cost per message: ${estimated_cost / summary_stats['summarized_nodes']:.6f}" if summary_stats['summarized_nodes'] > 0 else "  No summaries yet")
    
    # 10. Demonstrate different configurations
    print("\n⚙️ Configuration comparison:")
    configs = {
        "Aggressive": AGGRESSIVE_COMPRESSION,
        "Balanced": BALANCED,
        "Context Rich": CONTEXT_RICH
    }
    
    for name, test_config in configs.items():
        test_graph = ContextGraph("test", test_config)
        test_compiler = ContextCompiler(test_graph)
        # Copy nodes to test graph
        test_graph.nodes = graph.nodes.copy()
        test_graph.current_node_id = graph.current_node_id
        
        test_window = await test_compiler.compile_context(all_nodes[-1].id)
        print(f"\n  {name}:")
        print(f"    Context size: {test_window.total_tokens} tokens")
        print(f"    Distribution: {test_window.full_nodes}F/{test_window.summary_nodes}S/{test_window.title_nodes}T/{test_window.hidden_nodes}H")
    
    # 11. Save and restore
    print("\n💾 Persistence test:")
    graph_data = graph.to_dict()
    print(f"  Serialized size: {len(json.dumps(graph_data))} bytes")
    
    # Restore
    restored_graph = ContextGraph.from_dict(graph_data, config)
    print(f"  ✓ Restored graph with {len(restored_graph.nodes)} nodes")
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETE - System ready for production use!")
    print("="*80)
    
    return graph, standard_window


async def show_example_integration():
    """Show how this would integrate with the Architect."""
    print("\n\n📚 Example Architect Integration:")
    print("-" * 50)
    
    example_code = '''
class Architect:
    def __init__(self, project_path: str, config: ResolutionConfig = None):
        self.project_path = project_path
        self.config = config or BALANCED
        
        # Initialize context graph
        self.context_graph = ContextGraph(project_path, self.config)
        self.summarizer = ContextSummarizer(
            self.context_graph,
            SummarizationService()
        )
        self.compiler = ContextCompiler(self.context_graph)
        
    async def process_message(self, user_message: str) -> str:
        # Add user message to graph
        user_node = await self.context_graph.add_message(
            role="user",
            content=user_message,
            task_ids=self.current_task_ids
        )
        
        # Compile optimized context
        context_window = await self.compiler.compile_context(
            user_node.id,
            max_tokens=8000
        )
        
        # Use compiled context for response
        response = await self._generate_response(
            user_message,
            context_window.get_formatted_context()
        )
        
        # Add response to graph
        await self.context_graph.add_message(
            role="assistant",
            content=response,
            parent_id=user_node.id
        )
        
        # Trigger background summarization
        asyncio.create_task(self.summarizer.summarize_old_nodes())
        
        return response
'''
    
    print(example_code)
    print("\n✨ This provides intelligent context management that scales to any conversation length!")


if __name__ == "__main__":
    # Run the complete demo
    asyncio.run(simulate_long_conversation())
    
    # Show integration example
    asyncio.run(show_example_integration())