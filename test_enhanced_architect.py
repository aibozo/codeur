#!/usr/bin/env python3
"""
Quick test of the enhanced architect integration.
"""

import asyncio
from pathlib import Path
from src.architect.architect import Architect


async def test_enhanced_architect():
    """Test the enhanced architect with task graph."""
    print("Testing Enhanced Architect Integration")
    print("=" * 60)
    
    # Setup
    project_path = Path("./test_project")
    
    # Create architect with enhanced task graph
    architect = Architect(
        project_path=str(project_path),
        rag_service=None,  # No RAG for this test
        llm_client=None,  # No LLM for this test  
        use_enhanced_task_graph=True  # Enable enhanced mode
    )
    
    print(f"✓ Architect created with enhanced_task_graph={architect.use_enhanced_task_graph}")
    
    # Test that we have the tools
    if architect.architect_tools:
        print("✓ Architect tools initialized")
        functions = architect.get_enhanced_task_functions()
        print(f"✓ Available functions: {[f['name'] for f in functions]}")
    
    # Test task creation without LLM (fallback mode)
    print("\nTesting task creation (no LLM mode):")
    project_id = "test-blog-project"
    requirements = "Build a simple blog with user authentication, posts, and comments"
    task_graph = await architect.create_task_graph(project_id, requirements)
    
    print(f"✓ Created task graph for project: {task_graph.project_id}")
    print(f"✓ Number of tasks: {len(task_graph.tasks)}")
    print(f"✓ Root tasks: {[task.title for task in task_graph.tasks.values() if task.id in task_graph.root_tasks][:3]}")
    
    # Test enhanced features if available
    project_id = f"test_project_{project_path.name}"
    if project_id in architect.task_graph_managers:
        manager = architect.task_graph_managers[project_id]
        print(f"\n✓ Enhanced task manager available")
        
        # Get abstracted state
        state = manager.get_abstracted_state()
        print(f"✓ Total enhanced tasks: {state['total_tasks']}")
        print(f"✓ Communities detected: {len(state['communities'])}")
        
        # Test task tools
        if architect.architect_tools:
            # Test getting status
            status = await architect.architect_tools.get_task_status()
            print(f"✓ Task status retrieved: {status['status']}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_enhanced_architect())