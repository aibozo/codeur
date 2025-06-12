"""
Message queue integration for the Request Planner.

This module handles consuming ChangeRequest messages from the plan.in topic
and emitting Plan messages to downstream services.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import signal
import sys

from ..messaging import (
    MessageQueue, Message, QueueConfig,
    MessagingConfig, get_config, load_config_from_file
)
from ..messaging.kafka_impl import KafkaMessageQueue
from ..messaging.serializer import MessageSerializer, register_agent_messages
from ..messaging.base import DeadLetterHandler
from .planner import RequestPlanner
from .models import ChangeRequest as LocalChangeRequest

# Import protobuf messages (assumes protos are compiled)
try:
    from ..proto_gen import messages_pb2
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Protobuf messages not available. Run scripts/compile_protos.sh")

logger = logging.getLogger(__name__)


class RequestPlannerMessagingService:
    """
    Messaging service for the Request Planner.
    
    Handles:
    - Consuming ChangeRequest messages from plan.in
    - Processing requests through the planner
    - Emitting Plan messages
    - Dead letter queue handling
    - Graceful shutdown
    """
    
    def __init__(self, 
                 planner: Optional[RequestPlanner] = None,
                 config: Optional[MessagingConfig] = None):
        """
        Initialize the messaging service.
        
        Args:
            planner: Request planner instance (creates default if None)
            config: Messaging configuration (loads from env if None)
        """
        self.planner = planner or RequestPlanner()
        self.config = config or get_config()
        self.serializer = MessageSerializer()
        self.running = False
        
        # Register protobuf messages
        if PROTOBUF_AVAILABLE:
            register_agent_messages()
        
        # Create message queue
        queue_config = self.config.get_queue_config("request-planner")
        if self.config.broker_type == "kafka":
            self.message_queue = KafkaMessageQueue(queue_config)
        else:
            raise NotImplementedError(f"Broker type {self.config.broker_type} not implemented")
        
        # Create producer for emitting plans
        self.producer = self.message_queue.create_producer()
        
        # Create consumer for change requests
        self.consumer = self.message_queue.create_consumer(
            topics=["plan.in"],
            group_id=self.config.request_planner_group
        )
        
        # Create dead letter handler
        self.dead_letter_handler = DeadLetterHandler(
            self.message_queue,
            "plan.deadletter"
        )
        
        # Metrics
        self.metrics = {
            "requests_processed": 0,
            "plans_created": 0,
            "errors": 0,
            "dead_letters": 0
        }
        
        logger.info("Request Planner messaging service initialized")
    
    def _convert_protobuf_to_local(self, pb_request: 'messages_pb2.ChangeRequest') -> LocalChangeRequest:
        """Convert protobuf ChangeRequest to local model."""
        return LocalChangeRequest(
            id=pb_request.id,
            description=pb_request.description_md,
            repo=pb_request.repo,
            branch=pb_request.branch
        )
    
    def _convert_local_to_protobuf(self, local_plan) -> 'messages_pb2.Plan':
        """Convert local Plan model to protobuf."""
        pb_plan = messages_pb2.Plan()
        pb_plan.id = local_plan.id
        pb_plan.parent_request_id = local_plan.parent_request_id
        
        # Convert steps
        for step in local_plan.steps:
            pb_step = pb_plan.steps.add()
            pb_step.order = step.order
            pb_step.goal = step.goal
            pb_step.kind = messages_pb2.StepKind.Value(f"STEP_KIND_{step.kind.value.upper()}")
            pb_step.hints.extend(step.hints)
        
        # Add other fields
        pb_plan.rationale.extend(local_plan.rationale)
        pb_plan.affected_paths.extend(local_plan.affected_paths)
        pb_plan.complexity_label = messages_pb2.ComplexityLevel.Value(
            f"COMPLEXITY_{local_plan.complexity_label.value.upper()}"
        )
        pb_plan.estimated_tokens = local_plan.estimated_tokens
        
        # Add metadata
        import socket
        pb_plan.created_by_sha = f"{socket.gethostname()}-{self.planner.__class__.__name__}"
        
        return pb_plan
    
    async def handle_change_request(self, message: Message) -> None:
        """
        Handle a ChangeRequest message.
        
        Args:
            message: Message containing ChangeRequest
        """
        try:
            # Extract trace ID for distributed tracing
            trace_id = message.trace_id or f"req-{message.value.id}"
            logger.info(f"Processing ChangeRequest: {message.value.id} (trace: {trace_id})")
            
            # Convert protobuf to local model
            if PROTOBUF_AVAILABLE and isinstance(message.value, messages_pb2.ChangeRequest):
                local_request = self._convert_protobuf_to_local(message.value)
            else:
                # Assume it's already a dict or local model
                local_request = LocalChangeRequest(**message.value)
            
            # Load repository if specified
            if local_request.repo and local_request.repo != ".":
                self.planner.load_repository(local_request.repo, local_request.branch)
            
            # Create plan
            plan = self.planner.create_plan(local_request)
            
            # Convert to protobuf
            if PROTOBUF_AVAILABLE:
                pb_plan = self._convert_local_to_protobuf(plan)
            else:
                # Use dict representation
                pb_plan = {
                    "id": plan.id,
                    "parent_request_id": plan.parent_request_id,
                    "steps": [
                        {
                            "order": s.order,
                            "goal": s.goal,
                            "kind": s.kind.value,
                            "hints": s.hints
                        }
                        for s in plan.steps
                    ],
                    "rationale": plan.rationale,
                    "affected_paths": plan.affected_paths,
                    "complexity_label": plan.complexity_label.value,
                    "estimated_tokens": plan.estimated_tokens
                }
            
            # Emit plan to downstream services
            headers = {
                "trace_id": trace_id,
                "correlation_id": local_request.id,
                "agent": "request-planner"
            }
            
            # Send to Code Planner
            await self.producer.produce_async(
                topic="code.plan.in",
                value=pb_plan,
                key=plan.id,
                headers=headers
            )
            
            # Also send to plan.out for monitoring
            await self.producer.produce_async(
                topic="plan.out",
                value=pb_plan,
                key=plan.id,
                headers=headers
            )
            
            # Update metrics
            self.metrics["requests_processed"] += 1
            self.metrics["plans_created"] += 1
            
            logger.info(
                f"Successfully created and emitted plan {plan.id} "
                f"with {len(plan.steps)} steps"
            )
            
        except Exception as e:
            logger.error(f"Error processing ChangeRequest: {e}", exc_info=True)
            self.metrics["errors"] += 1
            
            # Send to dead letter queue
            self.dead_letter_handler.send_to_dead_letter(
                message,
                e,
                retry_count=0  # TODO: Implement retry logic
            )
            self.metrics["dead_letters"] += 1
            
            # Re-raise to prevent commit
            raise
    
    async def run_async(self) -> None:
        """Run the messaging service asynchronously."""
        self.running = True
        logger.info("Starting Request Planner messaging service...")
        
        # Set up signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Consume messages
            await self.consumer.consume_async(
                handler=self.handle_change_request,
                timeout=None  # Run forever
            )
        except Exception as e:
            logger.error(f"Error in message consumption: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    def run(self) -> None:
        """Run the messaging service synchronously."""
        asyncio.run(self.run_async())
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the service."""
        logger.info("Shutting down Request Planner messaging service...")
        
        # Stop consuming
        self.running = False
        
        # Flush any pending messages
        self.producer.flush(timeout=5)
        
        # Close resources
        self.consumer.close()
        self.producer.close()
        self.dead_letter_handler.close()
        self.message_queue.close()
        
        # Log final metrics
        logger.info(f"Final metrics: {self.metrics}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return self.metrics.copy()


def main():
    """Main entry point for running the Request Planner as a service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Request Planner Messaging Service")
    parser.add_argument(
        "--config",
        help="Path to messaging configuration file",
        default=None
    )
    parser.add_argument(
        "--repo",
        help="Default repository path",
        default="."
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    from ..core.logging import setup_logging
    setup_logging(getattr(logging, args.log_level))
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = get_config()
    
    # Create planner
    planner = RequestPlanner(repo_path=args.repo)
    
    # Create and run service
    service = RequestPlannerMessagingService(planner, config)
    
    try:
        service.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()