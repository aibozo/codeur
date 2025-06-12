#!/usr/bin/env python3
"""
Quick integration test for message queue and agents.
"""

import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.messaging.memory_impl import InMemoryMessageQueue
from src.messaging.base import QueueConfig
from src.proto_gen import messages_pb2
from src.core.logging import setup_logging
import logging

# Set up logging
setup_logging(logging.INFO)

def test_message_flow():
    """Test basic message flow through the queue."""
    print("\n=== Testing Message Queue Flow ===\n")
    
    # Create in-memory queue with config
    config = QueueConfig(
        name="test_queue",
        broker_url="memory://localhost",
        consumer_group="test_group",
        batch_size=10,
        max_retries=3
    )
    queue = InMemoryMessageQueue(config)
    
    # Create test messages
    print("📝 Creating test messages...")
    
    # 1. ChangeRequest
    request = messages_pb2.ChangeRequest()
    request.id = "test-req-001"
    request.repo = "test-repo"
    request.branch = "main"
    request.description_md = "Add error handling to API client"
    request.requester = "test_user"
    
    # 2. Plan
    plan = messages_pb2.Plan()
    plan.id = "test-plan-001"
    plan.parent_request_id = request.id
    plan.affected_paths.extend(["src/api.py", "tests/test_api.py"])
    plan.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    plan.estimated_tokens = 2000
    
    # Add steps
    step1 = plan.steps.add()
    step1.order = 1
    step1.goal = "Add try-except blocks to API calls"
    step1.kind = messages_pb2.STEP_KIND_EDIT
    step1.hints.extend(["Use requests.exceptions", "Add retry logic"])
    
    # 3. TaskBundle
    bundle = messages_pb2.TaskBundle()
    bundle.id = "test-bundle-001"
    bundle.parent_plan_id = plan.id
    
    # Add a task
    task = bundle.tasks.add()
    task.id = "test-task-001"
    task.parent_plan_id = plan.id
    task.step_number = 1
    task.goal = "Add error handling to fetch_data function"
    task.paths.append("src/api.py")
    task.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    
    # 4. CommitResult
    result = messages_pb2.CommitResult()
    result.task_id = task.id
    result.success = True
    result.commit_sha = "abc123def456"
    result.branch_name = "task/test-task-001"
    
    print("✓ Created 4 test messages")
    
    # Create producer
    producer = queue.create_producer()
    
    # Test publishing
    print("\n📤 Testing message publishing...")
    
    producer.produce("change_requests", request.SerializeToString())
    print("  ✓ Published ChangeRequest")
    
    producer.produce("plans", plan.SerializeToString())
    print("  ✓ Published Plan")
    
    producer.produce("task_bundles", bundle.SerializeToString())
    print("  ✓ Published TaskBundle")
    
    producer.produce("commit_results", result.SerializeToString())
    print("  ✓ Published CommitResult")
    
    producer.close()
    
    # Test consuming
    print("\n📥 Testing message consumption...")
    
    # Create consumer
    topics = ["change_requests", "plans", "task_bundles", "commit_results"]
    consumer = queue.create_consumer(topics)
    
    # Consume messages
    consumed_count = 0
    def message_handler(msg):
        nonlocal consumed_count
        consumed_count += 1
        print(f"  ✓ Consumed from {msg.topic}: {len(msg.value)} bytes")
    
    consumer.consume(message_handler, timeout=1.0)
    
    print(f"\n📊 Total messages consumed: {consumed_count}")
    
    consumer.close()
    
    print("\n✅ Message queue test completed!")


def test_protobuf_serialization():
    """Test protobuf serialization/deserialization."""
    print("\n\n=== Testing Protobuf Serialization ===\n")
    
    # Create a complex message
    task = messages_pb2.CodingTask()
    task.id = "serial-test"
    task.goal = "Test serialization"
    task.paths.extend(["file1.py", "file2.py"])
    task.blob_ids.extend(["blob1", "blob2", "blob3"])
    task.metadata["key1"] = "value1"
    task.metadata["key2"] = "value2"
    
    print("📝 Created CodingTask with:")
    print(f"  - ID: {task.id}")
    print(f"  - Goal: {task.goal}")
    print(f"  - Paths: {len(task.paths)}")
    print(f"  - Blobs: {len(task.blob_ids)}")
    print(f"  - Metadata: {len(task.metadata)} entries")
    
    # Serialize
    serialized = task.SerializeToString()
    print(f"\n📦 Serialized to {len(serialized)} bytes")
    
    # Deserialize
    task2 = messages_pb2.CodingTask()
    task2.ParseFromString(serialized)
    
    print("\n📋 Deserialized task:")
    print(f"  - ID: {task2.id}")
    print(f"  - Goal: {task2.goal}")
    print(f"  - Paths: {list(task2.paths)}")
    print(f"  - Metadata: {dict(task2.metadata)}")
    
    # Verify
    assert task2.id == task.id
    assert task2.goal == task.goal
    assert list(task2.paths) == list(task.paths)
    assert dict(task2.metadata) == dict(task.metadata)
    
    print("\n✅ Serialization test passed!")


def test_message_registry():
    """Test message creation directly."""
    print("\n\n=== Testing Message Creation ===\n")
    
    # Test creating various message types
    print("📚 Creating message instances:")
    
    # ChangeRequest
    req = messages_pb2.ChangeRequest()
    req.id = "test1"
    req.description_md = "Test request"
    print(f"  ✓ Created ChangeRequest: {req.id}")
    
    # Plan
    plan = messages_pb2.Plan()
    plan.id = "test2"
    plan.parent_request_id = "test1"
    print(f"  ✓ Created Plan: {plan.id}")
    
    # CodingTask
    task = messages_pb2.CodingTask()
    task.id = "test3"
    task.goal = "Test task"
    print(f"  ✓ Created CodingTask: {task.id}")
    
    # CommitResult
    result = messages_pb2.CommitResult()
    result.task_id = "test3"
    result.success = True
    print(f"  ✓ Created CommitResult for task: {result.task_id}")
    
    print("\n✅ Message creation test passed!")


if __name__ == "__main__":
    print("🚀 Quick Integration Test Suite\n")
    print(f"Environment:")
    print(f"  Python: {sys.version.split()[0]}")
    
    # Run tests
    test_message_flow()
    test_protobuf_serialization()
    test_message_registry()
    
    print("\n\n✅ All integration tests completed!")