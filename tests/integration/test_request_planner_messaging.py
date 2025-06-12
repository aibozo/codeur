"""
Integration tests for Request Planner messaging service.

These tests verify:
- Message consumption and production
- End-to-end plan creation flow
- Error handling and dead letter queues
- Graceful shutdown
"""

import pytest
import asyncio
import uuid
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.messaging import KafkaMessageQueue, QueueConfig, MessagingConfig
from src.messaging.serializer import MessageSerializer, register_agent_messages
from src.request_planner import RequestPlannerMessagingService, RequestPlanner
from src.proto_gen import messages_pb2


class TestRequestPlannerMessaging:
    """Integration tests for Request Planner messaging."""
    
    @pytest.fixture
    def messaging_config(self):
        """Create test messaging configuration."""
        config = MessagingConfig()
        config.broker_url = "localhost:9092"
        config.topics = {
            "plan.in": {"partitions": 1, "replication_factor": 1},
            "plan.out": {"partitions": 1, "replication_factor": 1},
            "code.plan.in": {"partitions": 1, "replication_factor": 1},
            "plan.deadletter": {"partitions": 1, "replication_factor": 1},
            "agent.events": {"partitions": 1, "replication_factor": 1},
        }
        return config
    
    @pytest.fixture
    def message_queue(self, messaging_config):
        """Create message queue instance."""
        queue_config = messaging_config.get_queue_config("test")
        mq = KafkaMessageQueue(queue_config)
        
        # Ensure topics exist
        for topic in messaging_config.topics:
            try:
                mq.create_topic(topic)
            except:
                pass  # Topic might already exist
        
        yield mq
        mq.close()
    
    @pytest.fixture
    async def planner_service(self, messaging_config):
        """Create Request Planner messaging service."""
        # Create a test planner with minimal setup
        planner = RequestPlanner(repo_path=".", use_llm=False)
        service = RequestPlannerMessagingService(planner, messaging_config)
        
        yield service
        
        # Cleanup
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_message_consumption(self, message_queue, planner_service):
        """Test that the service can consume messages."""
        # Register protobuf messages
        register_agent_messages()
        
        # Create a test ChangeRequest
        request = messages_pb2.ChangeRequest()
        request.id = f"test-{uuid.uuid4()}"
        request.description_md = "Add logging to main function"
        request.repo = "."
        request.branch = "main"
        request.requester = "test-user"
        
        # Produce the message
        producer = message_queue.create_producer()
        producer.produce("plan.in", request, key=request.id)
        producer.flush()
        
        # Track messages received
        messages_received = []
        
        # Create consumer to check plan.out
        consumer = message_queue.create_consumer(
            ["plan.out", "code.plan.in"],
            group_id="test-consumer"
        )
        
        # Run service briefly to process message
        service_task = asyncio.create_task(
            planner_service.consume.consume_async(
                planner_service.handle_change_request,
                timeout=5  # 5 seconds
            )
        )
        
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Check for output messages
        def collect_messages(msg):
            messages_received.append(msg)
        
        # Consume with timeout
        consume_task = asyncio.create_task(
            consumer.consume_async(collect_messages, timeout=3)
        )
        
        # Wait for tasks
        await asyncio.gather(service_task, consume_task, return_exceptions=True)
        
        # Verify we got output messages
        assert len(messages_received) >= 1, "Should have received at least one Plan message"
        
        # Check the plan
        plan_msg = None
        for msg in messages_received:
            if msg.topic in ["plan.out", "code.plan.in"]:
                plan_msg = msg
                break
        
        assert plan_msg is not None, "Should have received a Plan message"
        assert isinstance(plan_msg.value, messages_pb2.Plan), "Should be a Plan protobuf"
        assert plan_msg.value.parent_request_id == request.id
        assert len(plan_msg.value.steps) > 0, "Plan should have steps"
        
        # Cleanup
        consumer.close()
        producer.close()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, message_queue, planner_service):
        """Test error handling and dead letter queue."""
        register_agent_messages()
        
        # Create an invalid message (missing required fields)
        request = messages_pb2.ChangeRequest()
        request.id = f"test-error-{uuid.uuid4()}"
        # Missing description, repo, branch - should cause error
        
        producer = message_queue.create_producer()
        producer.produce("plan.in", request, key=request.id)
        producer.flush()
        
        # Track dead letters
        dead_letters = []
        
        # Consumer for dead letter queue
        dlq_consumer = message_queue.create_consumer(
            ["plan.deadletter"],
            group_id="test-dlq-consumer"
        )
        
        # Process the bad message
        service_task = asyncio.create_task(
            planner_service.consumer.consume_async(
                planner_service.handle_change_request,
                timeout=3
            )
        )
        
        # Collect dead letters
        def collect_dlq(msg):
            dead_letters.append(msg)
        
        dlq_task = asyncio.create_task(
            dlq_consumer.consume_async(collect_dlq, timeout=3)
        )
        
        # Wait for processing
        await asyncio.gather(service_task, dlq_task, return_exceptions=True)
        
        # Should have sent to dead letter queue
        assert len(dead_letters) > 0, "Should have dead letter messages"
        
        # Check dead letter has error info in headers
        dlq_msg = dead_letters[0]
        assert 'error_message' in dlq_msg.headers
        assert 'original_topic' in dlq_msg.headers
        assert dlq_msg.headers['original_topic'] == 'plan.in'
        
        # Cleanup
        dlq_consumer.close()
        producer.close()
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, planner_service):
        """Test graceful shutdown of the service."""
        # Start the service
        run_task = asyncio.create_task(planner_service.run_async())
        
        # Let it run briefly
        await asyncio.sleep(1)
        
        # Trigger shutdown
        planner_service.running = False
        
        # Wait for clean shutdown
        try:
            await asyncio.wait_for(run_task, timeout=5)
        except asyncio.TimeoutError:
            pytest.fail("Service did not shut down gracefully")
        
        # Check metrics were logged
        metrics = planner_service.get_metrics()
        assert isinstance(metrics, dict)
        assert 'requests_processed' in metrics
    
    def test_message_serialization(self):
        """Test protobuf message serialization."""
        serializer = MessageSerializer()
        
        # Create a test Plan
        plan = messages_pb2.Plan()
        plan.id = "test-plan-123"
        plan.parent_request_id = "test-request-123"
        
        step = plan.steps.add()
        step.order = 1
        step.goal = "Add logging"
        step.kind = messages_pb2.STEP_KIND_EDIT
        step.hints.append("main.py")
        
        plan.rationale.append("Improve debugging")
        plan.affected_paths.append("main.py")
        plan.complexity_label = messages_pb2.COMPLEXITY_MODERATE
        plan.estimated_tokens = 500
        
        # Serialize and deserialize
        serialized = serializer.serialize(plan)
        deserialized = serializer.deserialize(serialized, messages_pb2.Plan)
        
        # Verify
        assert deserialized.id == plan.id
        assert len(deserialized.steps) == 1
        assert deserialized.steps[0].goal == "Add logging"
        assert deserialized.complexity_label == messages_pb2.COMPLEXITY_MODERATE


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_request_flow(self, message_queue, messaging_config):
        """Test complete flow from ChangeRequest to Plan emission."""
        register_agent_messages()
        
        # Create service
        planner = RequestPlanner(repo_path=".", use_llm=False)
        service = RequestPlannerMessagingService(planner, messaging_config)
        
        # Create realistic ChangeRequest
        request = messages_pb2.ChangeRequest()
        request.id = f"e2e-{uuid.uuid4()}"
        request.description_md = """
        Add error handling to the file operations module.
        Specifically:
        - Add try-except blocks around file reads
        - Log errors appropriately
        - Return meaningful error messages
        """
        request.repo = "."
        request.branch = "main"
        request.requester = "developer@example.com"
        
        # Send request
        producer = message_queue.create_producer()
        producer.produce(
            "plan.in", 
            request, 
            key=request.id,
            headers={
                "trace_id": f"trace-{uuid.uuid4()}",
                "source": "test"
            }
        )
        producer.flush()
        
        # Collect all messages
        all_messages = []
        
        # Consumer for output
        consumer = message_queue.create_consumer(
            ["plan.out", "code.plan.in", "agent.events"],
            group_id="e2e-consumer"
        )
        
        # Run service
        service_task = asyncio.create_task(service.run_async())
        
        # Collect messages
        async def collect_with_timeout():
            def handler(msg):
                all_messages.append(msg)
                if len(all_messages) >= 2:  # Expect at least 2 messages
                    service.running = False
            
            await consumer.consume_async(handler, timeout=10)
        
        collect_task = asyncio.create_task(collect_with_timeout())
        
        # Wait for completion
        await asyncio.gather(service_task, collect_task, return_exceptions=True)
        
        # Verify results
        plan_messages = [m for m in all_messages if m.topic in ["plan.out", "code.plan.in"]]
        assert len(plan_messages) >= 1, "Should have emitted Plan messages"
        
        plan = plan_messages[0].value
        assert isinstance(plan, messages_pb2.Plan)
        assert plan.parent_request_id == request.id
        assert len(plan.steps) > 0
        assert any("error" in step.goal.lower() for step in plan.steps), \
               "Plan should address error handling"
        
        # Check trace propagation
        assert plan_messages[0].headers.get('trace_id') is not None
        assert plan_messages[0].headers.get('correlation_id') == request.id
        
        # Cleanup
        await service.shutdown()
        consumer.close()
        producer.close()


if __name__ == "__main__":
    # Run specific test
    import sys
    if len(sys.argv) > 1:
        pytest.main([__file__, "-v", "-k", sys.argv[1]])
    else:
        pytest.main([__file__, "-v"])