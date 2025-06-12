"""
Code Planner Messaging Service.

Integrates Code Planner with the message queue infrastructure to:
- Consume Plans from code.plan.in topic
- Emit TaskBundles to coding.task.in topic
"""

import asyncio
import logging
from typing import Optional
from ..messaging import (
    MessageQueue, Message, Producer, Consumer,
    MessagingConfig, QueueConfig, create_message_queue
)
from ..messaging.serializer import MessageSerializer, register_agent_messages
from ..messaging.base import DeadLetterHandler
from ..proto_gen import messages_pb2
from .code_planner import CodePlanner


logger = logging.getLogger(__name__)


class CodePlannerMessagingService:
    """
    Messaging service for Code Planner agent.
    
    Consumes: code.plan.in (Plans from Request Planner)
    Produces: coding.task.in (TaskBundles for Coding Agents)
    """
    
    def __init__(self, code_planner: CodePlanner, config: MessagingConfig):
        self.code_planner = code_planner
        self.config = config
        self.serializer = MessageSerializer()
        
        # Register protobuf messages
        register_agent_messages()
        
        # Message queue components (initialized in setup)
        self.message_queue: Optional[MessageQueue] = None
        self.producer: Optional[Producer] = None
        self.consumer: Optional[Consumer] = None
        self.dead_letter_handler: Optional[DeadLetterHandler] = None
        
        # Metrics
        self.metrics = {
            "plans_processed": 0,
            "task_bundles_created": 0,
            "errors": 0,
            "dead_letters": 0
        }
        
        self.running = False
    
    async def setup(self):
        """Set up messaging components."""
        logger.info("Setting up Code Planner messaging service")
        
        # Create message queue
        queue_config = self.config.get_queue_config("code-planner")
        self.message_queue = create_message_queue(queue_config)
        
        # Create producer and consumer
        self.producer = self.message_queue.create_producer()
        self.consumer = self.message_queue.create_consumer(
            topics=["code.plan.in"],
            group_id="code-planner-group"
        )
        
        # Set up dead letter handling
        self.dead_letter_handler = DeadLetterHandler(
            self.message_queue,
            "code.plan.deadletter"
        )
        
        logger.info("Code Planner messaging service setup complete")
    
    async def start(self):
        """Start consuming messages."""
        if not self.message_queue:
            await self.setup()
        
        self.running = True
        logger.info("Starting Code Planner message consumption")
        
        while self.running:
            try:
                # Consume messages
                await self.consumer.consume_async(
                    self.handle_plan,
                    timeout=30
                )
            except Exception as e:
                logger.error(f"Error in message consumption loop: {e}")
                self.metrics["errors"] += 1
                await asyncio.sleep(5)  # Back off on error
    
    async def handle_plan(self, message: Message) -> None:
        """
        Handle incoming Plan message.
        
        Args:
            message: Message containing a Plan
        """
        try:
            # Validate message type
            if not isinstance(message.value, messages_pb2.Plan):
                logger.error(f"Unexpected message type: {type(message.value)}")
                await self.dead_letter_handler.send(message, "Invalid message type")
                self.metrics["dead_letters"] += 1
                return
            
            plan = message.value
            logger.info(f"Processing Plan {plan.id} from topic {message.topic}")
            
            # Process the plan
            task_bundle = self.code_planner.process_plan(plan)
            
            # Validate the bundle
            if not self.code_planner.validate_task_bundle(task_bundle):
                logger.error(f"Invalid TaskBundle generated for plan {plan.id}")
                await self.dead_letter_handler.send(message, "Invalid TaskBundle")
                self.metrics["dead_letters"] += 1
                return
            
            # Emit TaskBundle to coding.task.in
            headers = {
                "plan_id": plan.id,
                "bundle_id": task_bundle.id,
                "task_count": str(len(task_bundle.tasks)),
                "strategy": task_bundle.execution_strategy
            }
            
            await self.producer.produce_async(
                topic="coding.task.in",
                value=task_bundle,
                key=task_bundle.id,
                headers=headers
            )
            
            logger.info(
                f"Emitted TaskBundle {task_bundle.id} with "
                f"{len(task_bundle.tasks)} tasks to coding.task.in"
            )
            
            # Update metrics
            self.metrics["plans_processed"] += 1
            self.metrics["task_bundles_created"] += 1
            
        except Exception as e:
            logger.error(f"Error processing plan: {e}", exc_info=True)
            self.metrics["errors"] += 1
            
            # Send to dead letter queue
            await self.dead_letter_handler.send(message, str(e))
            self.metrics["dead_letters"] += 1
    
    async def shutdown(self):
        """Gracefully shut down the service."""
        logger.info("Shutting down Code Planner messaging service")
        self.running = False
        
        # Close connections
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        
        logger.info("Code Planner messaging service shut down complete")
    
    def get_metrics(self) -> dict:
        """Get service metrics."""
        metrics = self.metrics.copy()
        metrics.update(self.code_planner.get_metrics())
        return metrics


async def run_code_planner_service(repo_path: str, config_path: Optional[str] = None):
    """
    Run the Code Planner messaging service.
    
    Args:
        repo_path: Path to the repository
        config_path: Optional path to messaging config
    """
    # Load configuration
    config = MessagingConfig.from_file(config_path) if config_path else MessagingConfig()
    
    # Create Code Planner
    code_planner = CodePlanner(repo_path)
    
    # Create and run service
    service = CodePlannerMessagingService(code_planner, config)
    
    try:
        await service.setup()
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.code_planner.messaging_service <repo_path> [config_path]")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the service
    asyncio.run(run_code_planner_service(repo_path, config_path))