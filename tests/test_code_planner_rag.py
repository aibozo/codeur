#!/usr/bin/env python3
"""
Test Code Planner RAG integration.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_planner.code_planner import CodePlanner
from src.code_planner.rag_integration import CodePlannerRAGIntegration
from src.proto_gen import messages_pb2
from src.core.logging import setup_logging
import logging

# Set up logging
setup_logging(logging.INFO)


def create_test_plan():
    """Create a test plan for Code Planner."""
    plan = messages_pb2.Plan()
    plan.id = "test-plan-rag-001"
    plan.parent_request_id = "request-001"
    plan.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    
    # Add steps
    step1 = plan.steps.add()
    step1.order = 1
    step1.goal = "Add error handling to database connection"
    step1.kind = messages_pb2.STEP_KIND_EDIT
    step1.hints.extend([
        "Add try-catch blocks",
        "Log errors appropriately",
        "Return meaningful error messages"
    ])
    
    step2 = plan.steps.add()
    step2.order = 2
    step2.goal = "Create unit tests for error handling"
    step2.kind = messages_pb2.STEP_KIND_TEST
    step2.hints.extend([
        "Test connection failures",
        "Test timeout scenarios",
        "Mock database errors"
    ])
    
    # Set affected paths
    plan.affected_paths.extend([
        "src/request_planner/context.py",
        "src/code_planner/task_generator.py"
    ])
    
    # Add file references to step hints for better detection
    step1.hints.append("in src/request_planner/context.py")
    step2.hints.append("for src/request_planner/context.py")
    
    return plan


def test_rag_integration():
    """Test RAG integration in Code Planner."""
    print("\n=== Testing Code Planner RAG Integration ===\n")
    
    # Initialize RAG integration separately to test it
    print("1. Testing standalone RAG integration...")
    rag = CodePlannerRAGIntegration(".")
    
    if rag.enabled:
        print("✓ RAG integration initialized successfully")
        
        # Test blob prefetching
        print("\n2. Testing blob prefetching...")
        plan = create_test_plan()
        step = plan.steps[0]
        
        blob_ids = rag.prefetch_blobs_for_step(
            step=step,
            affected_files=["src/request_planner/context.py"],
            k=5
        )
        
        print(f"✓ Prefetched {len(blob_ids)} blobs")
        for blob_id in blob_ids[:3]:
            print(f"  - {blob_id}")
        
        # Test similar implementation finding
        print("\n3. Testing similar implementation search...")
        similar = rag.find_similar_implementations(
            function_name="connect",
            implementation_type="error_handler",
            k=3
        )
        
        print(f"✓ Found {len(similar)} similar implementations")
        for impl in similar:
            print(f"  - {impl['file']}:{impl['line']} ({impl['symbol']})")
        
        # Test skeleton enhancement
        print("\n4. Testing skeleton patch enhancement...")
        enhanced = rag.enhance_skeleton_patch(
            file_path="src/request_planner/context.py",
            step=step,
            target_symbol="search"
        )
        
        if enhanced:
            print("✓ Generated enhanced skeleton patch")
            print(f"  Preview: {enhanced[:200]}...")
        else:
            print("⚠ No enhanced skeleton generated")
    else:
        print("⚠ RAG integration not enabled (check OPENAI_API_KEY)")
    
    # Test Code Planner with RAG
    print("\n5. Testing Code Planner with RAG...")
    planner = CodePlanner(repo_path=".", use_rag=True)
    
    # Process plan
    plan = create_test_plan()
    task_bundle = planner.process_plan(plan)
    
    print(f"✓ Generated task bundle: {task_bundle.id}")
    print(f"  Tasks: {len(task_bundle.tasks)}")
    
    # Check if tasks have blob IDs
    blobs_found = False
    for task in task_bundle.tasks:
        print(f"\n  Task: {task.goal[:50]}...")
        print(f"    Files: {', '.join(task.paths)}")
        print(f"    Blob IDs: {len(task.blob_ids)}")
        print(f"    Skeleton patches: {len(task.skeleton_patch)}")
        
        if task.blob_ids:
            blobs_found = True
            print(f"    Sample blob: {task.blob_ids[0]}")
    
    if blobs_found:
        print("\n✓ RAG blob prefetching is working!")
    else:
        print("\n⚠ No blob IDs found in tasks")
    
    print("\n✓ Code Planner RAG integration test completed!")


def test_without_rag():
    """Test Code Planner without RAG (fallback mode)."""
    print("\n\n=== Testing Code Planner without RAG ===\n")
    
    # Initialize without RAG
    planner = CodePlanner(repo_path=".", use_rag=False)
    
    # Process plan
    plan = create_test_plan()
    task_bundle = planner.process_plan(plan)
    
    print(f"✓ Generated task bundle: {task_bundle.id}")
    print(f"  Tasks: {len(task_bundle.tasks)}")
    
    # Check tasks
    for task in task_bundle.tasks:
        print(f"\n  Task: {task.goal[:50]}...")
        print(f"    Files: {', '.join(task.paths)}")
        print(f"    Blob IDs: {len(task.blob_ids)} (should be 0)")
        print(f"    Skeleton patches: {len(task.skeleton_patch)}")
    
    print("\n✓ Code Planner works without RAG!")


if __name__ == "__main__":
    # Check if RAG service is available
    has_openai = os.getenv("OPENAI_API_KEY") is not None
    
    if has_openai:
        print("OpenAI API key found - testing with RAG")
    else:
        print("No OpenAI API key - testing fallback mode")
    
    test_rag_integration()
    test_without_rag()