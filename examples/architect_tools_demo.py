#!/usr/bin/env python3
"""
Demo showing how the Architect LLM would use the simplified task creation tools.

This simulates how an LLM would interact with the tools using natural formats.
"""

import asyncio
import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.architect.task_graph_manager import TaskGraphManager, TaskGraphContext
from src.architect.llm_tools import ArchitectTools


async def demo_list_format():
    """Demo the simple list format (recommended for LLMs)."""
    print("\n" + "="*60)
    print("DEMO: Simple List Format (Recommended)")
    print("="*60)
    
    # Create context and tools
    context = TaskGraphContext(
        project_id="demo-list",
        project_path=Path("./demo_list_project")
    )
    manager = TaskGraphManager(context)
    tools = ArchitectTools(manager)
    
    # Simulate LLM creating tasks using list format
    task_content = """Build User Authentication:
  - Setup database schema (high, 2h)
  - Create User model:
    - Define user fields (1h)
    - Add password hashing (high, 1h)
    - Create validation rules (1h)
  - Implement JWT tokens (high, 3h, needs: Create User model)
  - Build authentication API:
    - Login endpoint (high, 2h)
    - Logout endpoint (1h)
    - Register endpoint (2h)
    - Password reset (medium, 3h)
  - Add middleware (medium, 2h, needs: Implement JWT tokens)
  - Write tests (low, 4h, needs: Build authentication API, Add middleware)"""
    
    print("\nLLM Input:")
    print(task_content)
    
    # Call the tool
    result = await tools.create_tasks(
        content=task_content,
        format="list"
    )
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    # Get status
    status = await tools.get_task_status()
    print("\nTask Status:")
    print(json.dumps(status, indent=2))
    
    return manager


async def demo_markdown_format():
    """Demo the markdown format (good for detailed descriptions)."""
    print("\n" + "="*60)
    print("DEMO: Markdown Format")
    print("="*60)
    
    # Create context and tools
    context = TaskGraphContext(
        project_id="demo-markdown",
        project_path=Path("./demo_markdown_project")
    )
    manager = TaskGraphManager(context)
    tools = ArchitectTools(manager)
    
    # Simulate LLM creating tasks using markdown
    task_content = """# E-commerce Platform

## Setup Infrastructure [critical] (8h)
Initialize the project with all necessary dependencies and configurations.
This includes database setup, environment configuration, and CI/CD pipelines.

### Database Setup [high] (3h)
- PostgreSQL installation
- Schema creation
- Migration system setup

### Environment Config (2h)
Create development, staging, and production configurations

## Product Catalog [high] (12h) [depends: Setup Infrastructure]
Build the core product management system

### Product Model [high] (4h)
Define product schema with categories, variants, and pricing

### Product API (6h) [depends: Product Model]
CRUD operations for products with search and filtering

## Shopping Cart [medium] (8h) [depends: Product Catalog]
Implement cart functionality with session management"""
    
    print("\nLLM Input:")
    print(task_content)
    
    # Call the tool
    result = await tools.create_tasks(
        content=task_content,
        format="markdown"
    )
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    return manager


async def demo_yaml_format():
    """Demo the YAML format (most structured)."""
    print("\n" + "="*60)
    print("DEMO: YAML Format")
    print("="*60)
    
    # Create context and tools
    context = TaskGraphContext(
        project_id="demo-yaml", 
        project_path=Path("./demo_yaml_project")
    )
    manager = TaskGraphManager(context)
    tools = ArchitectTools(manager)
    
    # Simulate LLM creating tasks using YAML
    task_content = """epic: Payment System
description: Complete payment processing system with multiple providers
priority: critical
tasks:
  - Payment Gateway Integration:
      priority: high
      hours: 8
      tasks:
        - Stripe Integration:
            hours: 4
            priority: high
        - PayPal Integration:
            hours: 4
  - Order Processing:
      needs: [Payment Gateway Integration]
      hours: 6
      tasks:
        - Order validation: 2h
        - Payment capture: 2h
        - Receipt generation: 2h
  - Refund System:
      needs: [Order Processing]
      priority: medium
      hours: 4"""
    
    print("\nLLM Input:")
    print(task_content)
    
    # Call the tool
    result = await tools.create_tasks(
        content=task_content,
        format="yaml"
    )
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    return manager


async def demo_adding_subtasks():
    """Demo adding subtasks to existing tasks."""
    print("\n" + "="*60)
    print("DEMO: Adding Subtasks")
    print("="*60)
    
    # Create initial structure
    context = TaskGraphContext(
        project_id="demo-subtasks",
        project_path=Path("./demo_subtasks_project")
    )
    manager = TaskGraphManager(context)
    tools = ArchitectTools(manager)
    
    # Create initial task
    await tools.create_tasks(
        content="  - Build API Gateway (high, 8h)",
        format="list",
        title="Microservices Setup"
    )
    
    # Now add subtasks
    subtasks_content = """- Setup Kong/Nginx (2h)
- Configure routes (2h) 
- Add authentication (high, 2h, needs: Setup Kong/Nginx)
- Implement rate limiting (1h, needs: Configure routes)
- Add monitoring (1h)"""
    
    print("\nAdding subtasks to 'Build API Gateway':")
    print(subtasks_content)
    
    result = await tools.add_subtasks(
        parent_task="Build API Gateway",
        subtasks=subtasks_content
    )
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    # Get detailed status
    status = await tools.get_task_status(detail_level="detailed")
    print("\nDetailed Status:")
    print(json.dumps(status, indent=2))
    
    return manager


async def demo_mixed_usage():
    """Demo a realistic mixed usage scenario."""
    print("\n" + "="*60)
    print("DEMO: Realistic Mixed Usage")
    print("="*60)
    
    context = TaskGraphContext(
        project_id="real-project",
        project_path=Path("./real_project")
    )
    manager = TaskGraphManager(context)
    tools = ArchitectTools(manager)
    
    # Step 1: Create initial high-level structure
    print("\n1. Creating high-level structure:")
    result1 = await tools.create_tasks(
        content="""
  - Backend Development (high)
  - Frontend Development (high)  
  - DevOps Setup (critical)
  - Testing & QA
  - Documentation""",
        format="list",
        title="SaaS Platform Development"
    )
    print(f"Created {result1.get('created_tasks')} tasks")
    
    # Step 2: Add backend subtasks
    print("\n2. Adding backend subtasks:")
    backend_tasks = """- Database design (critical, 4h)
- API framework setup (high, 2h)
- User service (high, 8h, needs: Database design, API framework setup)
- Auth service (critical, 6h, needs: User service)
- Billing service (high, 10h, needs: User service)
- Notification service (medium, 6h)"""
    
    result2 = await tools.add_subtasks(
        parent_task="Backend Development",
        subtasks=backend_tasks
    )
    print(f"Added {result2.get('subtasks_added')} subtasks")
    
    # Step 3: Update priority
    print("\n3. Updating priority of 'Documentation' to low:")
    result3 = await tools.update_task_priority(
        task_title="Documentation",
        new_priority="low"
    )
    print(f"Updated: {result3}")
    
    # Step 4: Get final status
    print("\n4. Final task graph status:")
    status = await tools.get_task_status()
    summary = status.get('summary', {})
    print(f"Total tasks: {summary.get('total_tasks')}")
    print(f"Communities detected: {len(summary.get('communities', []))}")
    for comm in summary.get('communities', []):
        print(f"  - {comm['name']}: {comm['tasks']} tasks")
    
    return manager


async def main():
    """Run all demos."""
    print("="*60)
    print("ARCHITECT TOOLS DEMONSTRATION")
    print("="*60)
    print("\nThis demo shows how an LLM can create complex task structures")
    print("using simple, natural formats instead of complex JSON.\n")
    
    # Run demos
    await demo_list_format()
    await demo_markdown_format()
    await demo_yaml_format()
    await demo_adding_subtasks()
    await demo_mixed_usage()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nKey takeaways:")
    print("- List format is simplest and recommended for most cases")
    print("- Markdown allows rich descriptions")
    print("- YAML provides most structure when needed")
    print("- Subtasks can be added incrementally")
    print("- Communities are auto-detected")
    print("- Single tool call can create entire hierarchies")


if __name__ == "__main__":
    asyncio.run(main())