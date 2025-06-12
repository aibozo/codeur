"""
In-memory implementation of the message queue for testing.

This provides a simple in-memory message queue that doesn't require
any external services like Kafka or RabbitMQ.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Deque
from collections import defaultdict, deque
import threading
import time
import uuid

from .base import (
    MessageQueue, Producer, Consumer, Message,
    MessageHandler, AsyncMessageHandler, QueueConfig
)
from .exceptions import ProducerException, ConsumerException

logger = logging.getLogger(__name__)


class InMemoryQueue:
    """Shared in-memory queue storage."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.queues: Dict[str, Deque[Message]] = defaultdict(deque)
        self.consumers: Dict[str, List['InMemoryConsumerImpl']] = defaultdict(list)
        self.topic_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        logger.info("In-memory queue storage initialized")
    
    def add_message(self, topic: str, message: Message) -> None:
        """Add a message to a topic."""
        with self._lock:
            self.queues[topic].append(message)
            # Notify consumers
            for consumer in self.consumers.get(topic, []):
                consumer._notify()
    
    def get_messages(self, topic: str, batch_size: int = 1) -> List[Message]:
        """Get messages from a topic."""
        with self._lock:
            messages = []
            queue = self.queues.get(topic, deque())
            for _ in range(min(batch_size, len(queue))):
                if queue:
                    messages.append(queue.popleft())
            return messages
    
    def create_topic(self, name: str, **metadata) -> None:
        """Create a topic."""
        with self._lock:
            if name not in self.topic_metadata:
                self.topic_metadata[name] = metadata
                self.queues[name] = deque()
                logger.info(f"Created in-memory topic: {name}")
    
    def delete_topic(self, name: str) -> None:
        """Delete a topic."""
        with self._lock:
            self.topic_metadata.pop(name, None)
            self.queues.pop(name, None)
            self.consumers.pop(name, None)
            logger.info(f"Deleted in-memory topic: {name}")
    
    def register_consumer(self, topic: str, consumer: 'InMemoryConsumerImpl') -> None:
        """Register a consumer for a topic."""
        with self._lock:
            self.consumers[topic].append(consumer)
    
    def unregister_consumer(self, topic: str, consumer: 'InMemoryConsumerImpl') -> None:
        """Unregister a consumer."""
        with self._lock:
            if topic in self.consumers:
                self.consumers[topic].remove(consumer)


class InMemoryProducerImpl(Producer):
    """In-memory implementation of Producer."""
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.queue_storage = InMemoryQueue()
        self._closed = False
    
    def produce(self,
                topic: str,
                value: Any,
                key: Optional[str] = None,
                headers: Optional[Dict[str, str]] = None) -> None:
        """Produce a message."""
        if self._closed:
            raise ProducerException("Producer is closed")
        
        # Create message
        message = Message(
            topic=topic,
            key=key,
            value=value,
            headers=headers or {},
            timestamp=int(time.time() * 1000),
            offset=None,  # Will be set by consumer
            partition=0  # Single partition for in-memory
        )
        
        # Add to queue
        self.queue_storage.add_message(topic, message)
        logger.debug(f"Produced message to {topic}")
    
    async def produce_async(self,
                           topic: str,
                           value: Any,
                           key: Optional[str] = None,
                           headers: Optional[Dict[str, str]] = None) -> None:
        """Async produce (just wraps sync version)."""
        self.produce(topic, value, key, headers)
    
    def flush(self, timeout: Optional[float] = None) -> None:
        """No-op for in-memory."""
        pass
    
    def close(self) -> None:
        """Close the producer."""
        self._closed = True


class InMemoryConsumerImpl(Consumer):
    """In-memory implementation of Consumer."""
    
    def __init__(self, config: QueueConfig, topics: List[str]):
        self.config = config
        self.topics = topics
        self.queue_storage = InMemoryQueue()
        self._running = False
        self._closed = False
        self._notify_event = threading.Event()
        self._offset_counters = defaultdict(int)
        
        # Register with queue storage
        for topic in topics:
            self.queue_storage.register_consumer(topic, self)
    
    def _notify(self):
        """Notify consumer of new messages."""
        self._notify_event.set()
    
    def consume(self,
                handler: MessageHandler,
                timeout: Optional[float] = None) -> None:
        """Consume messages."""
        if self._closed:
            raise ConsumerException("Consumer is closed")
        
        self._running = True
        start_time = time.time()
        
        try:
            while self._running:
                if timeout and (time.time() - start_time) > timeout:
                    break
                
                # Wait for messages with timeout
                if self._notify_event.wait(timeout=0.1):
                    self._notify_event.clear()
                
                # Process messages from all topics
                for topic in self.topics:
                    messages = self.queue_storage.get_messages(
                        topic, 
                        self.config.batch_size
                    )
                    
                    for message in messages:
                        # Set offset
                        message.offset = self._offset_counters[topic]
                        self._offset_counters[topic] += 1
                        
                        try:
                            handler(message)
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            # Re-queue message for retry
                            self.queue_storage.add_message(topic, message)
                            
        finally:
            self._running = False
    
    async def consume_async(self,
                           handler: AsyncMessageHandler,
                           timeout: Optional[float] = None) -> None:
        """Async consume."""
        if self._closed:
            raise ConsumerException("Consumer is closed")
        
        self._running = True
        start_time = asyncio.get_event_loop().time()
        
        try:
            while self._running:
                if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                    break
                
                # Process messages from all topics
                for topic in self.topics:
                    messages = self.queue_storage.get_messages(
                        topic,
                        self.config.batch_size
                    )
                    
                    for message in messages:
                        # Set offset
                        message.offset = self._offset_counters[topic]
                        self._offset_counters[topic] += 1
                        
                        try:
                            await handler(message)
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            # Re-queue message for retry
                            self.queue_storage.add_message(topic, message)
                
                # Small delay to prevent busy loop
                await asyncio.sleep(0.01)
                
        finally:
            self._running = False
    
    def commit(self, message: Optional[Message] = None) -> None:
        """No-op for in-memory (auto-commit)."""
        pass
    
    def close(self) -> None:
        """Close the consumer."""
        self._running = False
        self._closed = True
        
        # Unregister from queue storage
        for topic in self.topics:
            self.queue_storage.unregister_consumer(topic, self)
    
    def pause(self, partitions: Optional[List[int]] = None) -> None:
        """Pause consumption."""
        self._running = False
    
    def resume(self, partitions: Optional[List[int]] = None) -> None:
        """Resume consumption."""
        self._running = True


class InMemoryMessageQueue(MessageQueue):
    """In-memory implementation of MessageQueue."""
    
    def __init__(self, config: QueueConfig):
        super().__init__(config)
        self.queue_storage = InMemoryQueue()
        logger.info("In-memory message queue initialized")
    
    def create_producer(self) -> Producer:
        """Create a producer."""
        return InMemoryProducerImpl(self.config)
    
    def create_consumer(self,
                       topics: List[str],
                       group_id: Optional[str] = None) -> Consumer:
        """Create a consumer."""
        # For in-memory, group_id doesn't affect behavior
        return InMemoryConsumerImpl(self.config, topics)
    
    def create_topic(self,
                    name: str,
                    partitions: int = 1,
                    replication_factor: int = 1,
                    config: Optional[Dict[str, str]] = None) -> None:
        """Create a topic."""
        self.queue_storage.create_topic(
            name,
            partitions=partitions,
            replication_factor=replication_factor,
            config=config or {}
        )
    
    def delete_topic(self, name: str) -> None:
        """Delete a topic."""
        self.queue_storage.delete_topic(name)
    
    def list_topics(self) -> List[str]:
        """List all topics."""
        return list(self.queue_storage.topic_metadata.keys())
    
    def get_topic_metadata(self, topic: str) -> Dict[str, Any]:
        """Get topic metadata."""
        metadata = self.queue_storage.topic_metadata.get(topic, {})
        return {
            'name': topic,
            'partitions': metadata.get('partitions', 1),
            'messages_count': len(self.queue_storage.queues.get(topic, []))
        }
    
    def health_check(self) -> bool:
        """Always healthy for in-memory."""
        return True
    
    def close(self) -> None:
        """Close the message queue."""
        logger.info("In-memory message queue closed")