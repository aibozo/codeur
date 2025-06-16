#!/usr/bin/env python3
"""
Example of using the Architect with enhanced task graph features.

This shows how the integrated system works with LLM function calling
to create hierarchical task structures.
"""

import asyncio
import os
from pathlib import Path
from src.architect.architect import Architect


async def main():
    """Demonstrate enhanced architect usage."""
    # Set up project path
    project_path = Path("./my_saas_project")
    project_path.mkdir(exist_ok=True)
    
    # Create architect with enhanced features
    print("Creating Enhanced Architect...")
    architect = Architect(
        project_path=str(project_path),
        use_enhanced_task_graph=True  # Enable enhanced task graph
    )
    
    # Example 1: Analyze requirements
    print("\n1. Analyzing Project Requirements...")
    requirements = """
    Build a SaaS platform for project management with:
    - User authentication and teams
    - Project boards with kanban view
    - Task assignment and tracking
    - Real-time updates
    - File attachments
    - Commenting system
    - Email notifications
    - API for integrations
    """
    
    await architect.analyze_project_requirements(requirements)
    print("✓ Requirements analyzed")
    
    # Example 2: Create task graph
    print("\n2. Creating Task Graph...")
    project_id = "saas-pm-platform"
    task_graph = await architect.create_task_graph(project_id, requirements)
    
    print(f"✓ Created {len(task_graph.tasks)} tasks")
    print(f"✓ Root tasks: {len(task_graph.root_tasks)}")
    print(f"✓ Critical path: {len(task_graph.get_critical_path())} tasks")
    
    # Example 3: Access enhanced features (if LLM is available)
    if hasattr(architect, 'architect_tools') and architect.architect_tools:
        print("\n3. Using Enhanced Task Tools...")
        
        # Get task status
        status = await architect.architect_tools.get_task_status()
        if status['status'] == 'success':
            summary = status.get('summary', {})
            print(f"✓ Total tasks (enhanced): {summary.get('total_tasks', 0)}")
            print(f"✓ Communities detected: {len(summary.get('communities', []))}")
            
            # Show communities
            for comm in summary.get('communities', []):
                print(f"  - {comm['name']}: {comm['tasks']} tasks")
        
        # Add more detailed tasks using natural language
        print("\n4. Adding Detailed Authentication Tasks...")
        result = await architect.architect_tools.add_subtasks(
            parent_task="Implement Authentication",
            subtasks="""
- Setup JWT tokens (high, 2h)
- Create login endpoint (high, 2h)
- Add OAuth2 support:
  - Google OAuth (2h)
  - GitHub OAuth (2h)
- Implement 2FA (critical, 3h)
- Session management (1h)
- Password reset flow (medium, 2h)
"""
        )
        
        if result['status'] == 'success':
            print(f"✓ Added {result['subtasks_added']} authentication subtasks")
    else:
        print("\n(Enhanced tools not available - need OpenAI API key)")
    
    # Example 4: Get abstracted state for context management
    if project_id in architect.task_graph_managers:
        print("\n5. Getting Abstracted State...")
        manager = architect.task_graph_managers[project_id]
        state = manager.get_abstracted_state()
        
        print(f"✓ Total tasks: {state['total_tasks']}")
        print(f"✓ Completed: {state['completed_tasks']}")
        print(f"✓ Top-level tasks: {len(state['top_level_tasks'])}")
        
        # Show first few top-level tasks
        for task in state['top_level_tasks'][:3]:
            print(f"  - {task['title']} ({task['status']})")
    
    # Example 5: Save the enhanced graph
    if hasattr(architect, 'save_enhanced_task_graph'):
        print("\n6. Saving Enhanced Task Graph...")
        save_path = architect.save_enhanced_task_graph(project_id)
        if save_path:
            print(f"✓ Saved to: {save_path}")
    
    print("\n✅ Demo complete!")
    print("\nNote: To use LLM features, set OPENAI_API_KEY environment variable")


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  No OPENAI_API_KEY found - running in limited mode")
        print("   Set OPENAI_API_KEY to enable LLM-powered task creation")
        print()
    
    asyncio.run(main())