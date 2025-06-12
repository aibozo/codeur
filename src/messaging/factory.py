"""
Factory functions for creating message queue instances.
"""

from typing import Optional
from .base import MessageQueue, QueueConfig
from .memory_impl import InMemoryMessageQueue
from .exceptions import MessagingException

# Import Kafka with graceful fallback
try:
    from .kafka_impl import KafkaMessageQueue
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False


def create_message_queue(config: QueueConfig) -> MessageQueue:
    """
    Create a message queue instance based on configuration.
    
    Args:
        config: Queue configuration
        
    Returns:
        MessageQueue instance
        
    Raises:
        MessagingException: If the requested broker type is not available
    """
    broker_type = _get_broker_type(config.broker_url)
    
    if broker_type == "memory":
        return InMemoryMessageQueue(config)
    
    elif broker_type == "kafka":
        if not KAFKA_AVAILABLE:
            raise MessagingException(
                "Kafka support not available. Install confluent-kafka-python package."
            )
        return KafkaMessageQueue(config)
    
    elif broker_type == "amqp":
        raise MessagingException("AMQP support not yet implemented")
    
    else:
        raise MessagingException(f"Unknown broker type: {broker_type}")


def _get_broker_type(broker_url: str) -> str:
    """Extract broker type from URL."""
    if broker_url.startswith("memory://"):
        return "memory"
    elif broker_url.startswith("kafka://"):
        return "kafka"
    elif broker_url.startswith("amqp://"):
        return "amqp"
    elif ":" in broker_url and not broker_url.startswith("http"):
        # Assume host:port format is Kafka
        return "kafka"
    else:
        raise MessagingException(f"Cannot determine broker type from URL: {broker_url}")