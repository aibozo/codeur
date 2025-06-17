#!/usr/bin/env python3
"""
Demonstration of the Deep Context Passing System.

This script shows how the architect creates detailed phased implementation plans
and how execution agents can retrieve rich context for their tasks.
"""

import asyncio
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.architect import (
    PlanManager, PlanAwareArchitect, PlanAPI,
    TaskGraphManager, PhaseType
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class MockRAGClient:
    """Mock RAG client for demonstration."""
    
    def __init__(self):
        self.documents = []
    
    def index_documents(self, documents):
        """Mock document indexing."""
        self.documents.extend(documents)
        logger.info(f"Indexed {len(documents)} documents in RAG")
    
    def query(self, query: str, top_k: int = 5, filter: dict = None):
        """Mock query implementation."""
        # Simple keyword matching for demo
        results = []
        for doc in self.documents:
            if query.lower() in doc["content"].lower():
                results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": 0.85  # Mock relevance score
                })
        
        return {"documents": results[:top_k]}


async def demonstrate_plan_creation():
    """Demonstrate creating a detailed implementation plan."""
    print("\n" + "="*80)
    print("DEEP CONTEXT PASSING SYSTEM DEMONSTRATION")
    print("="*80)
    
    # Initialize components
    project_path = "/tmp/demo_project"
    rag_client = MockRAGClient()
    
    # Create plan manager with RAG integration
    plan_manager = PlanManager(
        base_path=".agent",
        rag_client=rag_client,
        auto_index=True
    )
    
    # Create task graph manager
    task_manager = TaskGraphManager()
    
    # Create plan-aware architect
    architect = PlanAwareArchitect(
        project_path=project_path,
        task_manager=task_manager,
        plan_manager=plan_manager,
        llm_client=None  # Using template-based approach for demo
    )
    
    # Create an implementation plan
    print("\n1. Creating Implementation Plan")
    print("-" * 40)
    
    requirement = "Real-time notification system with WebSocket support"
    plan = await architect.create_implementation_plan(
        requirement=requirement,
        project_type="feature",
        scope="medium"
    )
    
    print(f"✓ Created plan: {plan.name}")
    print(f"  - ID: {plan.id}")
    print(f"  - Phases: {len(plan.phases)}")
    print(f"  - Total chunks: {len(plan.get_all_chunks())}")
    
    # Display plan structure
    print("\n2. Plan Structure")
    print("-" * 40)
    
    for phase in plan.phases:
        print(f"\n  Phase {phase.order + 1}: {phase.name} ({phase.phase_type.value})")
        print(f"  Estimated: {phase.estimated_days} days")
        
        for milestone in phase.milestones:
            print(f"    └─ Milestone: {milestone.title}")
            print(f"       Chunks: {len(milestone.chunks)}")
            
            for chunk in milestone.chunks[:2]:  # Show first 2 chunks
                print(f"         - {chunk.title} (priority: {chunk.priority})")
    
    # Activate the plan
    plan_manager.activate_plan(plan.id)
    print(f"\n✓ Plan activated")
    
    # Get task graph info
    if plan.task_graph_id:
        task_graph = task_manager.get_graph(plan.task_graph_id)
        if task_graph:
            tasks = task_manager.get_all_tasks(plan.task_graph_id)
            print(f"\n✓ Created task graph with {len(tasks)} tasks")
    
    return plan_manager, plan


async def demonstrate_context_retrieval(plan_manager, plan):
    """Demonstrate how agents retrieve context."""
    print("\n\n3. Context Retrieval for Execution Agents")
    print("-" * 40)
    
    # Create Plan API for agents
    plan_api = PlanAPI(plan_manager)
    
    # Get the first task from the plan
    task_graph = plan_manager.task_manager.get_graph(plan.task_graph_id) if hasattr(plan_manager, 'task_manager') else None
    
    # Simulate task execution
    print("\nSimulating agent retrieving context for a task...")
    
    # Get ready tasks
    ready_tasks = plan_manager.get_ready_tasks_from_plans()
    
    if ready_tasks:
        # Take the first ready task
        task_info = ready_tasks[0]
        print(f"\n  Task: {task_info['milestone_title']}")
        print(f"  Phase: {task_info['phase_name']}")
        print(f"  Priority: {task_info['priority']}")
        
        # Create a mock task ID (in real system, this would come from task graph)
        mock_task_id = f"task_{task_info['milestone_id']}"
        
        # Map chunks to this task
        chunk_ids = [chunk['id'] for chunk in task_info['chunks']]
        if chunk_ids:
            plan_manager.map_task_to_chunks(mock_task_id, chunk_ids)
        
        # Agent retrieves context
        print("\n4. Agent Context Retrieval")
        print("-" * 40)
        
        context = plan_api.get_task_context(
            task_id=mock_task_id,
            task_description=task_info['milestone_description']
        )
        
        # Display retrieved context
        print("\nRetrieved Context:")
        
        if context.get("implementation_guide"):
            print("\n  Implementation Guide Preview:")
            lines = context["implementation_guide"].split("\n")[:10]
            for line in lines:
                print(f"    {line}")
            if len(context["implementation_guide"].split("\n")) > 10:
                print("    ... (truncated)")
        
        if context.get("technical_context"):
            tech = context["technical_context"]
            if tech.get("architectural_patterns"):
                print("\n  Architectural Patterns:")
                for pattern in tech["architectural_patterns"]:
                    print(f"    - {pattern}")
        
        if context.get("technologies"):
            print("\n  Technologies:")
            for tech in context["technologies"][:5]:
                print(f"    - {tech}")
        
        if context.get("test_requirements"):
            print("\n  Test Requirements:")
            for req in context["test_requirements"][:3]:
                print(f"    - {req}")
        
        if context.get("acceptance_criteria"):
            print("\n  Acceptance Criteria:")
            for criteria in context["acceptance_criteria"][:3]:
                print(f"    - {criteria}")
        
        # Demonstrate semantic search
        print("\n5. Semantic Context Search")
        print("-" * 40)
        
        similar = plan_api.get_similar_implementations(
            "WebSocket connection handling",
            limit=3
        )
        
        if similar:
            print("\n  Found similar implementations:")
            for impl in similar:
                print(f"    - {impl.get('metadata', {}).get('chunk_title', 'Unknown')}")
        else:
            print("\n  No similar implementations found (this is normal for demo)")
    
    return plan_api


async def demonstrate_plan_templates():
    """Demonstrate plan template system."""
    print("\n\n6. Plan Template System")
    print("-" * 40)
    
    plan_manager = PlanManager(base_path=".agent")
    
    # List available templates
    templates = plan_manager.storage.list_templates()
    
    if not templates:
        print("\n  Creating a template from our plan...")
        
        # Load our plan
        plans = plan_manager.list_plans()
        if plans:
            plan = plan_manager.load_plan(plans[0]["id"])
            if plan:
                # Save as template
                success = plan_manager.storage.save_template(
                    "realtime_feature_template",
                    plan
                )
                if success:
                    print("  ✓ Saved plan as template: 'realtime_feature_template'")
    
    # Create new plan from template
    print("\n  Creating new plan from template...")
    new_plan = plan_manager.create_plan_from_template(
        "realtime_feature_template",
        {
            "name": "Chat System Implementation",
            "description": "Real-time chat system with rooms",
            "technology_stack": ["Python", "FastAPI", "Redis", "PostgreSQL"]
        }
    )
    
    if new_plan:
        print(f"  ✓ Created new plan: {new_plan.name}")
        print(f"    - Based on template")
        print(f"    - Customized technology stack")


async def demonstrate_metrics():
    """Demonstrate plan metrics and reporting."""
    print("\n\n7. Plan Metrics and Analytics")
    print("-" * 40)
    
    plan_manager = PlanManager(base_path=".agent")
    
    # Get overall metrics
    metrics = plan_manager.get_plan_metrics()
    
    print("\n  Plan Metrics:")
    print(f"    - Total Plans: {metrics['total_plans']}")
    print(f"    - Active Plans: {metrics['active_plans']}")
    print(f"    - Completed Plans: {metrics['completed_plans']}")
    print(f"    - Total Milestones: {metrics['total_milestones']}")
    print(f"    - Average Completion: {metrics['average_completion']:.1f}%")
    
    if metrics['plans_by_type']:
        print("\n  Plans by Type:")
        for ptype, count in metrics['plans_by_type'].items():
            print(f"    - {ptype}: {count}")


def display_summary():
    """Display summary of the deep context passing system."""
    print("\n\n" + "="*80)
    print("DEEP CONTEXT PASSING SYSTEM SUMMARY")
    print("="*80)
    
    print("""
The Deep Context Passing System provides:

1. **Phased Implementation Plans**
   - Structured phases (Research → Design → Implementation → Testing)
   - Milestones with clear deliverables and success criteria
   - Context chunks with implementation guidance

2. **Rich Context for Agents**
   - Step-by-step implementation guides
   - Technical context and architectural decisions
   - Relevant files and code examples
   - Test requirements and acceptance criteria

3. **Semantic Search Integration**
   - RAG-indexed plan components
   - Find similar implementations
   - Technology-specific examples

4. **Plan Management**
   - Templates for common project types
   - Progress tracking and metrics
   - Plan archival and reuse

5. **Clean API for Agents**
   - Simple context retrieval
   - No need to understand plan structure
   - Automatic context aggregation

This system ensures that execution agents always have the context they need
to implement features correctly, following architectural decisions and best
practices established during planning.
""")


async def main():
    """Run the demonstration."""
    try:
        # Create and demonstrate plans
        plan_manager, plan = await demonstrate_plan_creation()
        
        # Demonstrate context retrieval
        plan_api = await demonstrate_context_retrieval(plan_manager, plan)
        
        # Demonstrate templates
        await demonstrate_plan_templates()
        
        # Show metrics
        await demonstrate_metrics()
        
        # Display summary
        display_summary()
        
        print("\n✓ Demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())