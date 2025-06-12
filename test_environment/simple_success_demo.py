#!/usr/bin/env python3
"""
Simplified demo showing successful agent pipeline with a simpler task.
"""

import sys
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.messaging.memory_impl import InMemoryMessageQueue
from src.messaging.base import QueueConfig
from src.proto_gen import messages_pb2
from src.request_planner import RequestPlanner
from src.request_planner.models import ChangeRequest as InternalChangeRequest
from src.code_planner import CodePlanner
from src.coding_agent import CodingAgent
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging


async def simple_demo():
    """Run a simple demo with a basic change request."""
    
    # Setup logging (less verbose)
    setup_logging(logging.WARNING)
    
    print("\n=== Agent Pipeline Demo ===\n")
    
    # Initialize components
    repo_path = Path(__file__).parent / "test_repo"
    
    # Initialize agents
    print("🔧 Initializing agents...")
    request_planner = RequestPlanner()
    code_planner = CodePlanner(str(repo_path))
    
    # RAG Service
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    rag_client = RAGClient(service=rag_service)
    
    # LLM Client
    llm_client = LLMClient()
    
    # Coding Agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client
    )
    
    print("✓ All agents initialized\n")
    
    # Create a simpler change request
    print("📝 Creating change request...")
    
    request = InternalChangeRequest(
        id=f"req-{uuid.uuid4().hex[:8]}",
        description="Add a simple docstring to the get_user method in src/api_client.py explaining that it fetches user data from the API",
        repo=str(repo_path),
        branch="master",
        requester="demo_user"
    )
    
    print(f"Request: {request.description}\n")
    
    # Step 1: Request Planner
    print("🎯 Step 1: Request Planner creating plan...")
    try:
        plan = request_planner.create_plan(request)
        print(f"✓ Created plan with {len(plan.steps)} steps:")
        for step in plan.steps[:3]:  # Show first 3 steps
            print(f"  {step.order}. {step.goal[:60]}...")
    except Exception as e:
        print(f"❌ Request Planner failed: {e}")
        return
    
    # Convert to protobuf
    pb_plan = messages_pb2.Plan()
    pb_plan.id = plan.id
    pb_plan.parent_request_id = plan.parent_request_id
    pb_plan.affected_paths.extend(plan.affected_paths)
    pb_plan.complexity_label = getattr(
        messages_pb2,
        f"COMPLEXITY_{plan.complexity_label.value.upper()}"
    )
    pb_plan.estimated_tokens = plan.estimated_tokens
    
    for step in plan.steps:
        pb_step = pb_plan.steps.add()
        pb_step.order = step.order
        pb_step.goal = step.goal
        pb_step.kind = getattr(
            messages_pb2,
            f"STEP_KIND_{step.kind.value.upper()}"
        )
        pb_step.hints.extend(step.hints)
    
    # Step 2: Code Planner
    print(f"\n📋 Step 2: Code Planner creating tasks...")
    try:
        task_bundle = code_planner.process_plan(pb_plan)
        print(f"✓ Created {len(task_bundle.tasks)} tasks")
        
        # Just process the first task for demo
        if task_bundle.tasks:
            first_task = task_bundle.tasks[0]
            print(f"\nProcessing first task: {first_task.goal[:60]}...")
            
            # Step 3: Coding Agent
            print(f"\n💻 Step 3: Coding Agent working...")
            result = coding_agent.process_task(first_task)
            
            if result.status.name == "SUCCESS":
                print(f"✅ Success! Created commit: {result.commit_sha[:8] if result.commit_sha else 'N/A'}")
                if result.branch_name:
                    print(f"   Branch: {result.branch_name}")
                    
                # Show the actual change
                import subprocess
                try:
                    diff = subprocess.run(
                        ["git", "show", "--stat", result.commit_sha],
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )
                    if diff.returncode == 0:
                        print("\n📄 Changes made:")
                        print(diff.stdout)
                except:
                    pass
            else:
                print(f"❌ Task failed: {result.status.name}")
                for note in result.notes[:3]:
                    print(f"   - {note}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Demo complete!")


if __name__ == "__main__":
    asyncio.run(simple_demo())