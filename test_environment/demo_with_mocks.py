#!/usr/bin/env python3
"""
Demo the agent system with mock LLM responses.
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.request_planner.models import ChangeRequest, Plan, Step, StepKind, ComplexityLevel
from src.proto_gen import messages_pb2
from src.code_planner import CodePlanner
from src.core.logging import setup_logging


def demo_agent_flow():
    """Demo the agent flow with mocks."""
    
    # Setup logging
    setup_logging(logging.INFO)
    
    print("\n=== Agent System Demo ===\n")
    
    # Repository path
    repo_path = Path(__file__).parent / "test_repo"
    
    # Step 1: Create a change request
    print("📝 Step 1: Change Request")
    print("-" * 50)
    
    request = ChangeRequest(
        id=f"req-{uuid.uuid4().hex[:8]}",
        requester="demo_user",
        repo=str(repo_path),
        branch="master",
        description="Add error handling to API client for network failures"
    )
    
    print(f"ID: {request.id}")
    print(f"Description: {request.description}")
    print(f"Repository: {request.repo}")
    
    # Step 2: Create a plan (mock Request Planner output)
    print("\n🎯 Step 2: Request Planner → Plan")
    print("-" * 50)
    
    plan = Plan(
        id=f"plan-{uuid.uuid4().hex[:8]}",
        parent_request_id=request.id,
        steps=[
            Step(
                order=1,
                goal="Add try-except blocks to all HTTP requests in api_client.py",
                kind=StepKind.EDIT,
                hints=[
                    "Wrap requests.get/post/put/delete calls",
                    "Handle requests.exceptions.RequestException",
                    "Add timeout parameter"
                ]
            ),
            Step(
                order=2,
                goal="Add retry logic with exponential backoff",
                kind=StepKind.EDIT,
                hints=[
                    "Use tenacity library or implement custom retry",
                    "Max 3 retries",
                    "Exponential backoff starting at 1 second"
                ]
            ),
            Step(
                order=3,
                goal="Update tests to cover error scenarios",
                kind=StepKind.TEST,
                hints=[
                    "Mock network failures",
                    "Test retry behavior",
                    "Verify error messages"
                ]
            )
        ],
        rationale=[
            "API client currently has no error handling",
            "Network failures will crash the application",
            "Retry logic needed for transient failures"
        ],
        affected_paths=["src/api_client.py", "tests/test_api_client.py"],
        complexity_label=ComplexityLevel.MODERATE,
        estimated_tokens=1500
    )
    
    print(f"Plan ID: {plan.id}")
    print(f"Complexity: {plan.complexity_label.value}")
    print(f"Steps: {len(plan.steps)}")
    for step in plan.steps:
        print(f"  {step.order}. {step.goal}")
    
    # Convert to protobuf
    pb_plan = messages_pb2.Plan()
    pb_plan.id = plan.id
    pb_plan.parent_request_id = plan.parent_request_id
    pb_plan.affected_paths.extend(plan.affected_paths)
    pb_plan.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    pb_plan.estimated_tokens = plan.estimated_tokens
    
    for step in plan.steps:
        pb_step = pb_plan.steps.add()
        pb_step.order = step.order
        pb_step.goal = step.goal
        pb_step.kind = getattr(messages_pb2, f"STEP_KIND_{step.kind.value.upper()}")
        pb_step.hints.extend(step.hints)
    
    # Step 3: Code Planner creates tasks
    print("\n📋 Step 3: Code Planner → Task Bundle")
    print("-" * 50)
    
    code_planner = CodePlanner(str(repo_path))
    
    try:
        # Process the plan
        task_bundle = code_planner.process_plan(pb_plan)
        
        print(f"Task Bundle ID: {task_bundle.id}")
        print(f"Execution Strategy: {task_bundle.execution_strategy}")
        print(f"Tasks: {len(task_bundle.tasks)}")
        
        for i, task in enumerate(task_bundle.tasks):
            print(f"\n  Task {i+1}: {task.id}")
            print(f"    Goal: {task.goal[:60]}...")
            print(f"    Files: {', '.join(task.paths)}")
            print(f"    Complexity: {task.complexity_label}")
            print(f"    Dependencies: {', '.join(task.depends_on) if task.depends_on else 'None'}")
            
            if task.skeleton_patch:
                print(f"    Skeleton patches: {len(task.skeleton_patch)}")
                
    except Exception as e:
        print(f"❌ Code Planner error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Show what Coding Agent would do
    print("\n💻 Step 4: Coding Agent (Mock)")
    print("-" * 50)
    
    print("Without an LLM, the Coding Agent would:")
    print("1. Create a feature branch for each task")
    print("2. Gather context using RAG service")
    print("3. Generate patches using LLM")
    print("4. Validate changes (syntax, linting, tests)")
    print("5. Create git commits")
    
    # Show the actual files that would be modified
    print("\n📄 Files to be modified:")
    with open(repo_path / "src" / "api_client.py", "r") as f:
        content = f.read()
        print(f"\nsrc/api_client.py ({len(content)} chars):")
        print("  Current: No error handling")
        print("  After: Try-except blocks, timeouts, retry logic")
    
    print("\n✅ Demo complete!")
    print("\nTo see the full pipeline with actual code generation:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Run the test again")


if __name__ == "__main__":
    demo_agent_flow()