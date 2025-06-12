#!/usr/bin/env python3
"""
Test with in-memory message queue (no Kafka required).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.messaging import InMemoryMessageQueue, MessagingConfig, QueueConfig
from src.messaging.serializer import register_agent_messages
from src.request_planner import RequestPlannerMessagingService, RequestPlanner
from src.proto_gen import messages_pb2


async def test_in_memory_flow():
    """Test Request Planner with in-memory queue."""
    print("🧪 Testing Request Planner with In-Memory Queue")
    print("=" * 50)
    
    # Register protobuf messages
    register_agent_messages()
    
    # Create in-memory configuration
    config = MessagingConfig()
    config.broker_type = "memory"
    config.broker_url = "memory://localhost"
    
    # Create in-memory queue
    queue_config = config.get_queue_config("test")
    mq = InMemoryMessageQueue(queue_config)
    print("✓ Created in-memory message queue")
    
    # Create topics
    for topic in ["plan.in", "plan.out", "code.plan.in", "plan.deadletter"]:
        mq.create_topic(topic)
    print("✓ Created topics")
    
    # Create Request Planner service with custom queue
    planner = RequestPlanner(repo_path=".", use_llm=False)
    
    # Override the service to use our in-memory queue
    class TestMessagingService(RequestPlannerMessagingService):
        def __init__(self, planner, config):
            self.planner = planner
            self.config = config
            from src.messaging.serializer import MessageSerializer
            self.serializer = MessageSerializer()
            register_agent_messages()
            self.running = False
            
            # Use in-memory queue
            self.message_queue = mq
            self.producer = mq.create_producer()
            self.consumer = mq.create_consumer(["plan.in"], group_id="test")
            
            from src.messaging.base import DeadLetterHandler
            self.dead_letter_handler = DeadLetterHandler(mq, "plan.deadletter")
            
            self.metrics = {
                "requests_processed": 0,
                "plans_created": 0,
                "errors": 0,
                "dead_letters": 0
            }
    
    service = TestMessagingService(planner, config)
    print("✓ Created Request Planner service")
    
    # Create test request
    request = messages_pb2.ChangeRequest()
    request.id = "test-123"
    request.description_md = "Add error handling to the main function"
    request.repo = "."
    request.branch = "main"
    request.requester = "test@example.com"
    
    # Send request
    producer = mq.create_producer()
    producer.produce("plan.in", request, key=request.id)
    print(f"\n✓ Sent test request: {request.id}")
    
    # Create consumer for results
    results = []
    consumer = mq.create_consumer(["plan.out", "code.plan.in"], group_id="test-consumer")
    
    # Process in background
    async def process_messages():
        await service.consumer.consume_async(
            service.handle_change_request,
            timeout=2
        )
    
    # Collect results
    def collect_results(msg):
        results.append(msg)
        print(f"\n✓ Received {msg.topic}: {type(msg.value).__name__}")
        if isinstance(msg.value, messages_pb2.Plan):
            print(f"  Steps: {len(msg.value.steps)}")
            for i, step in enumerate(msg.value.steps[:3], 1):
                print(f"  {i}. {step.goal}")
    
    # Run test
    process_task = asyncio.create_task(process_messages())
    
    # Wait a bit for processing
    await asyncio.sleep(0.5)
    
    # Collect results
    consumer.consume(collect_results, timeout=1)
    
    # Wait for processing to complete
    await process_task
    
    # Check results
    print(f"\n📊 Results:")
    print(f"  Messages received: {len(results)}")
    print(f"  Metrics: {service.get_metrics()}")
    
    success = len(results) >= 2  # Should get plan.out and code.plan.in
    
    # Cleanup
    consumer.close()
    producer.close()
    await service.shutdown()
    
    return success


def main():
    """Run the test."""
    print("\n🚀 In-Memory Message Queue Test")
    print("No external services required!\n")
    
    success = asyncio.run(test_in_memory_flow())
    
    if success:
        print("\n✅ Test passed!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())