"""
Base classes and interfaces for message queue abstraction.

This module defines the abstract interfaces that all message queue
implementations must follow, allowing easy switching between Kafka,
AMQP, or other messaging systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, List, TypeVar, Generic
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DeliveryMode(Enum):
    """Message delivery guarantees."""
    AT_MOST_ONCE = "at_most_once"    # Fire and forget
    AT_LEAST_ONCE = "at_least_once"  # May have duplicates
    EXACTLY_ONCE = "exactly_once"     # No duplicates (harder to implement)


@dataclass
class QueueConfig:
    """Configuration for a message queue."""
    name: str
    broker_url: str
    delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    max_retries: int = 3
    retry_delay_ms: int = 1000
    dead_letter_queue: Optional[str] = None
    consumer_group: Optional[str] = None
    batch_size: int = 1
    poll_timeout_ms: int = 1000
    extra_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_config is None:
            self.extra_config = {}


@dataclass
class Message(Generic[T]):
    """Generic message wrapper."""
    topic: str
    key: Optional[str]
    value: T
    headers: Dict[str, str]
    timestamp: Optional[int] = None
    offset: Optional[int] = None
    partition: Optional[int] = None
    
    @property
    def trace_id(self) -> Optional[str]:
        """Get trace ID from headers."""
        return self.headers.get('trace_id')
    
    @property
    def correlation_id(self) -> Optional[str]:
        """Get correlation ID from headers."""
        return self.headers.get('correlation_id')


# Type alias for message handler functions
MessageHandler = Callable[[Message], None]
AsyncMessageHandler = Callable[[Message], asyncio.Future]


class Producer(ABC):
    """Abstract producer interface."""
    
    @abstractmethod
    def __init__(self, config: QueueConfig):
        """Initialize the producer with configuration."""
        pass
    
    @abstractmethod
    def produce(self, 
                topic: str, 
                value: Any,
                key: Optional[str] = None,
                headers: Optional[Dict[str, str]] = None) -> None:
        """
        Produce a message to a topic.
        
        Args:
            topic: Target topic/queue name
            value: Message value (will be serialized)
            key: Optional message key for partitioning
            headers: Optional message headers
        """
        pass
    
    @abstractmethod
    async def produce_async(self,
                           topic: str,
                           value: Any,
                           key: Optional[str] = None,
                           headers: Optional[Dict[str, str]] = None) -> None:
        """Async version of produce."""
        pass
    
    @abstractmethod
    def flush(self, timeout: Optional[float] = None) -> None:
        """Flush any pending messages."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the producer and release resources."""
        pass


class Consumer(ABC):
    """Abstract consumer interface."""
    
    @abstractmethod
    def __init__(self, config: QueueConfig, topics: List[str]):
        """Initialize the consumer with configuration and topics."""
        pass
    
    @abstractmethod
    def consume(self, 
                handler: MessageHandler,
                timeout: Optional[float] = None) -> None:
        """
        Consume messages synchronously.
        
        Args:
            handler: Function to handle each message
            timeout: Optional timeout in seconds
        """
        pass
    
    @abstractmethod
    async def consume_async(self,
                           handler: AsyncMessageHandler,
                           timeout: Optional[float] = None) -> None:
        """Async version of consume."""
        pass
    
    @abstractmethod
    def commit(self, message: Optional[Message] = None) -> None:
        """
        Commit message offset.
        
        Args:
            message: Specific message to commit, or None for auto-commit
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the consumer and release resources."""
        pass
    
    @abstractmethod
    def pause(self, partitions: Optional[List[int]] = None) -> None:
        """Pause consumption from specified partitions."""
        pass
    
    @abstractmethod
    def resume(self, partitions: Optional[List[int]] = None) -> None:
        """Resume consumption from specified partitions."""
        pass


class MessageQueue(ABC):
    """
    Abstract message queue interface.
    
    This is the main entry point for creating producers and consumers.
    """
    
    @abstractmethod
    def __init__(self, config: QueueConfig):
        """Initialize the message queue with configuration."""
        self.config = config
    
    @abstractmethod
    def create_producer(self) -> Producer:
        """Create a new producer instance."""
        pass
    
    @abstractmethod
    def create_consumer(self, 
                       topics: List[str],
                       group_id: Optional[str] = None) -> Consumer:
        """
        Create a new consumer instance.
        
        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID for coordinated consumption
        """
        pass
    
    @abstractmethod
    def create_topic(self, 
                    name: str,
                    partitions: int = 1,
                    replication_factor: int = 1,
                    config: Optional[Dict[str, str]] = None) -> None:
        """
        Create a new topic (admin operation).
        
        Args:
            name: Topic name
            partitions: Number of partitions
            replication_factor: Replication factor
            config: Additional topic configuration
        """
        pass
    
    @abstractmethod
    def delete_topic(self, name: str) -> None:
        """Delete a topic (admin operation)."""
        pass
    
    @abstractmethod
    def list_topics(self) -> List[str]:
        """List all available topics."""
        pass
    
    @abstractmethod
    def get_topic_metadata(self, topic: str) -> Dict[str, Any]:
        """Get metadata for a specific topic."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the message queue is healthy and accessible."""
        pass
    
    def close(self) -> None:
        """Close all connections and release resources."""
        pass


class DeadLetterHandler:
    """
    Handles dead letter queue operations.
    
    Messages that fail processing after max retries are sent here.
    """
    
    def __init__(self, 
                 queue: MessageQueue,
                 dead_letter_topic: str):
        """
        Initialize dead letter handler.
        
        Args:
            queue: Message queue instance
            dead_letter_topic: Name of the dead letter topic
        """
        self.queue = queue
        self.dead_letter_topic = dead_letter_topic
        self.producer = queue.create_producer()
    
    def send_to_dead_letter(self,
                           original_message: Message,
                           error: Exception,
                           retry_count: int) -> None:
        """
        Send a message to the dead letter queue.
        
        Args:
            original_message: The original failed message
            error: The exception that caused the failure
            retry_count: Number of retries attempted
        """
        headers = original_message.headers.copy()
        headers.update({
            'original_topic': original_message.topic,
            'error_message': str(error),
            'error_type': type(error).__name__,
            'retry_count': str(retry_count),
            'failed_at': str(int(asyncio.get_event_loop().time() * 1000))
        })
        
        self.producer.produce(
            topic=self.dead_letter_topic,
            value=original_message.value,
            key=original_message.key,
            headers=headers
        )
        
        logger.warning(
            f"Sent message to dead letter queue: {self.dead_letter_topic} "
            f"(error: {type(error).__name__})"
        )
    
    async def send(self, original_message: Message, error_msg: str) -> None:
        """
        Async convenience method to send a message to dead letter queue.
        
        Args:
            original_message: The original failed message
            error_msg: Error message string
        """
        error = Exception(error_msg)
        self.send_to_dead_letter(original_message, error, 0)
    
    def __del__(self):
        """Clean up producer on deletion."""
        if hasattr(self, 'producer') and self.producer:
            self.producer.close()
    def close(self) -> None:
        """Close the dead letter handler."""
        self.producer.close()