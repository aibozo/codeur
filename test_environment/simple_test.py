#!/usr/bin/env python3
"""
Simple test of the agent system using in-memory message queue.
"""

import sys
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.messaging.memory_impl import InMemoryMessageQueue
from src.messaging.base import QueueConfig
from src.proto_gen import messages_pb2
from src.request_planner import RequestPlanner
from src.code_planner import CodePlanner
from src.coding_agent import CodingAgent
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging


async def test_agent_pipeline():
    """Test the agent pipeline with a simple example."""
    
    # Setup logging
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("\n=== Testing Agent Pipeline ===\n")
    
    # Initialize components
    repo_path = Path(__file__).parent / "test_repo"
    
    # Create message queue
    config = QueueConfig(
        name="test_queue",
        broker_url="memory://localhost",
        consumer_group="test_group"
    )
    queue = InMemoryMessageQueue(config)
    
    # Initialize agents
    print("🔧 Initializing agents...")
    
    # Request Planner
    request_planner = RequestPlanner()
    
    # Code Planner
    code_planner = CodePlanner(str(repo_path))
    
    # RAG Service (optional)
    rag_client = None
    try:
        rag_dir = repo_path / ".rag"
        rag_service = RAGService(persist_directory=str(rag_dir))
        rag_client = RAGClient(service=rag_service)
        if rag_client.is_available():
            print("✓ RAG service available")
            # Index the test repository
            results = rag_client.index_directory(
                directory=str(repo_path),
                extensions=[".py"]
            )
            print(f"✓ Indexed {len(results)} files")
    except Exception as e:
        print(f"⚠ RAG service not available: {e}")
    
    # LLM Client (optional)
    llm_client = None
    try:
        llm_client = LLMClient()
        print("✓ LLM client initialized")
    except Exception as e:
        print(f"⚠ LLM client not available: {e}")
    
    # Coding Agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client
    )
    
    # Create a test change request
    print("\n📝 Creating test change request...")
    
    request = messages_pb2.ChangeRequest()
    request.id = f"req-{uuid.uuid4().hex[:8]}"
    request.requester = "test_user"
    request.repo = str(repo_path)
    request.branch = "master"
    request.description_md = """Add error handling to the API client in src/api_client.py for network failures. Add try-except blocks around HTTP requests, add timeout parameter, and return None on error instead of crashing."""
    
    print(f"Request ID: {request.id}")
    lines = request.description_md.split('\n')
    print(f"Description: {lines[1] if len(lines) > 1 else 'N/A'}")
    
    # Step 1: Request Planner creates a plan
    print("\n🎯 Step 1: Request Planner creating plan...")
    try:
        # Convert protobuf to internal model
        from src.request_planner.models import ChangeRequest as InternalChangeRequest
        internal_request = InternalChangeRequest(
            id=request.id,
            description=request.description_md,  # Map description_md to description
            repo=request.repo,
            branch=request.branch,
            requester=request.requester
        )
        
        plan = request_planner.create_plan(internal_request)
        print(f"✓ Created plan: {plan.id}")
        print(f"  Steps: {len(plan.steps)}")
        for step in plan.steps:
            print(f"    {step.order}. {step.goal}")
    except Exception as e:
        print(f"✗ Request Planner failed: {e}")
        import traceback
        traceback.print_exc()
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
    
    # Step 2: Code Planner creates tasks
    print("\n📋 Step 2: Code Planner creating tasks...")
    try:
        task_bundle = code_planner.process_plan(pb_plan)
        print(f"✓ Created task bundle: {task_bundle.id}")
        print(f"  Tasks: {len(task_bundle.tasks)}")
        for task in task_bundle.tasks:
            print(f"    - {task.id}: {task.goal[:50]}...")
    except Exception as e:
        print(f"✗ Code Planner failed: {e}")
        return
    
    # Step 3: Coding Agent processes tasks
    print("\n💻 Step 3: Coding Agent processing tasks...")
    
    if not llm_client:
        print("⚠ Skipping Coding Agent (no LLM client)")
        print("\nTo see full pipeline, set OPENAI_API_KEY environment variable")
        return
    
    for task in task_bundle.tasks:
        print(f"\nProcessing task: {task.id}")
        try:
            result = coding_agent.process_task(task)
            
            if result.status.name == "SUCCESS":
                print(f"✓ Success! Commit: {result.commit_sha[:8] if result.commit_sha else 'N/A'}")
                if result.branch_name:
                    print(f"  Branch: {result.branch_name}")
            else:
                print(f"✗ Failed: {result.status.name}")
                for note in result.notes:
                    print(f"  - {note}")
                    
        except Exception as e:
            print(f"✗ Error processing task: {e}")
    
    print("\n✅ Pipeline test complete!")


async def main():
    """Run the test."""
    await test_agent_pipeline()


if __name__ == "__main__":
    asyncio.run(main())