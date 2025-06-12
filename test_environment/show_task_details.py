#!/usr/bin/env python3
"""
Show detailed task information from Code Planner.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from demo_with_mocks import *

def show_task_details():
    """Run demo and show detailed task information."""
    
    # Setup
    setup_logging(logging.WARNING)  # Less verbose
    repo_path = Path(__file__).parent / "test_repo"
    
    # Create the same plan as demo
    plan = Plan(
        id=f"plan-{uuid.uuid4().hex[:8]}",
        parent_request_id="req-demo",
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
            )
        ],
        rationale=["API client needs error handling"],
        affected_paths=["src/api_client.py"],
        complexity_label=ComplexityLevel.MODERATE,
        estimated_tokens=1000
    )
    
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
        pb_step.kind = messages_pb2.STEP_KIND_EDIT
        pb_step.hints.extend(step.hints)
    
    # Process with Code Planner
    code_planner = CodePlanner(str(repo_path))
    task_bundle = code_planner.process_plan(pb_plan)
    
    print("\n=== Detailed Task Information ===\n")
    
    for i, task in enumerate(task_bundle.tasks):
        print(f"Task {i+1}: {task.id}")
        print("=" * 60)
        print(f"Goal: {task.goal}")
        print(f"Base commit: {task.base_commit_sha}")
        print(f"Estimated tokens: {task.estimated_tokens}")
        
        if task.blob_ids:
            print(f"\nPre-fetched RAG blobs ({len(task.blob_ids)}):")
            for blob_id in task.blob_ids[:3]:
                print(f"  - {blob_id}")
        
        if task.skeleton_patch:
            print(f"\nSkeleton patches ({len(task.skeleton_patch)}):")
            for j, patch in enumerate(task.skeleton_patch):
                print(f"\n--- Skeleton Patch {j+1} ---")
                print(patch)
                print("--- End Patch ---")
        
        if task.metadata:
            print(f"\nMetadata:")
            for key, value in task.metadata.items():
                print(f"  {key}: {value}")
        
        print("\n")
    
    # Show AST analysis
    print("=== AST Analysis Results ===\n")
    
    analyzer = code_planner.analyzer
    
    # Analyze the API client file
    api_file = repo_path / "src" / "api_client.py"
    ast_data = analyzer.parse_file(str(api_file))
    
    if ast_data:
        print(f"File: {api_file}")
        print(f"Functions found: {len(ast_data['functions'])}")
        for func in ast_data['functions']:
            print(f"  - {func['name']} (lines {func['start_line']}-{func['end_line']})")
            print(f"    Complexity: {func.get('complexity', 'N/A')}")
        
        print(f"\nImports: {len(ast_data['imports'])}")
        for imp in ast_data['imports']:
            print(f"  - {imp}")
    
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    show_task_details()