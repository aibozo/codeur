#!/usr/bin/env python3
"""
Simple end-to-end test for Request Planner messaging.

This test can be run manually to verify the system works.
"""

import asyncio
import uuid
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.messaging import KafkaMessageQueue, MessagingConfig, get_config
from src.messaging.serializer import register_agent_messages
from src.request_planner import RequestPlannerMessagingService, RequestPlanner
from src.proto_gen import messages_pb2


async def test_request_planner_flow():
    """Test the complete Request Planner flow."""
    print("Starting Request Planner E2E Test")
    print("=" * 50)
    
    # Register protobuf messages
    register_agent_messages()
    
    # Create configuration
    config = get_config()
    config.broker_url = "localhost:9092"
    
    # Create message queue
    queue_config = config.get_queue_config("e2e-test")
    mq = KafkaMessageQueue(queue_config)
    
    # Check health
    if not mq.health_check():
        print("❌ Kafka is not running. Please start it with:")
        print("   python scripts/setup_messaging.py --start-kafka")
        return False
    
    print("✓ Connected to Kafka")
    
    # Create Request Planner service
    planner = RequestPlanner(repo_path=".", use_llm=False)
    service = RequestPlannerMessagingService(planner, config)
    print("✓ Created Request Planner service")
    
    # Create a test request
    request = messages_pb2.ChangeRequest()
    request.id = f"e2e-test-{uuid.uuid4().hex[:8]}"
    request.description_md = """
    Add comprehensive error handling to the file operations module.
    This should include:
    - Try-except blocks for all file operations
    - Proper logging of errors
    - User-friendly error messages
    - Graceful degradation on failures
    """
    request.repo = "."
    request.branch = "main"
    request.requester = "test@example.com"
    
    print(f"\n✓ Created test request: {request.id}")
    print(f"  Description: {request.description_md[:50]}...")
    
    # Send the request
    producer = mq.create_producer()
    producer.produce(
        "plan.in",
        request,
        key=request.id,
        headers={
            "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
            "test": "true"
        }
    )
    producer.flush()
    print("\n✓ Sent ChangeRequest to plan.in topic")
    
    # Create consumer for results
    consumer = mq.create_consumer(
        ["plan.out", "code.plan.in"],
        group_id="e2e-test-consumer"
    )
    
    # Collect results
    results = []
    
    async def collect_results(timeout=10):
        """Collect results with timeout."""
        start_time = asyncio.get_event_loop().time()
        
        def handler(msg):
            results.append(msg)
            print(f"\n✓ Received message on topic: {msg.topic}")
            if isinstance(msg.value, messages_pb2.Plan):
                plan = msg.value
                print(f"  Plan ID: {plan.id}")
                print(f"  Steps: {len(plan.steps)}")
                print(f"  Complexity: {messages_pb2.ComplexityLevel.Name(plan.complexity_label)}")
                
                for i, step in enumerate(plan.steps[:3], 1):
                    print(f"  Step {i}: {step.goal}")
                
                if len(plan.steps) > 3:
                    print(f"  ... and {len(plan.steps) - 3} more steps")
        
        # Start the service
        service_task = asyncio.create_task(service.run_async())
        
        # Consume messages
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if len(results) >= 2:  # We expect at least 2 messages (plan.out and code.plan.in)
                break
            
            # Poll for messages
            await asyncio.sleep(0.1)
            consumer.consume(handler, timeout=0.1)
        
        # Stop the service
        service.running = False
        await asyncio.sleep(0.5)  # Give it time to shutdown
        
        return len(results) > 0
    
    # Run the test
    print("\n⏳ Waiting for Request Planner to process...")
    success = await collect_results()
    
    # Check results
    if success:
        print(f"\n✅ Test completed successfully!")
        print(f"   Received {len(results)} messages")
        
        # Verify the plan
        plan_messages = [r for r in results if isinstance(r.value, messages_pb2.Plan)]
        if plan_messages:
            plan = plan_messages[0].value
            print(f"\n📋 Generated Plan Summary:")
            print(f"   - ID: {plan.id}")
            print(f"   - Parent Request: {plan.parent_request_id}")
            print(f"   - Total Steps: {len(plan.steps)}")
            print(f"   - Affected Files: {len(plan.affected_paths)}")
            print(f"   - Rationale Points: {len(plan.rationale)}")
            
            if plan.rationale:
                print(f"\n📝 Rationale:")
                for r in plan.rationale[:3]:
                    print(f"   - {r}")
    else:
        print("\n❌ Test failed - no messages received")
    
    # Cleanup
    await service.shutdown()
    consumer.close()
    producer.close()
    mq.close()
    
    return success


def main():
    """Run the test."""
    print("\n🚀 Request Planner E2E Test")
    print("This test verifies the complete message flow:\n")
    print("  1. Send ChangeRequest → plan.in")
    print("  2. Request Planner processes it")
    print("  3. Receive Plan → plan.out & code.plan.in")
    print("\nMake sure Kafka is running!")
    print("=" * 50)
    
    # Run the async test
    success = asyncio.run(test_request_planner_flow())
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())