"""
Kafka implementation of the message queue interfaces.

This module provides Kafka-based implementations of Producer, Consumer,
and MessageQueue using the confluent-kafka library.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from confluent_kafka import Producer as KafkaProducer
from confluent_kafka import Consumer as KafkaConsumer
from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
import json

from .base import (
    MessageQueue, Producer, Consumer, Message,
    MessageHandler, AsyncMessageHandler, QueueConfig,
    DeliveryMode
)
from .exceptions import (
    ProducerException, ConsumerException,
    ConnectionException, TopicException
)
from .serializer import MessageSerializer, message_registry

logger = logging.getLogger(__name__)


class KafkaProducerImpl(Producer):
    """Kafka implementation of the Producer interface."""
    
    def __init__(self, config: QueueConfig):
        """Initialize Kafka producer."""
        self.config = config
        self.serializer = MessageSerializer()
        
        # Build Kafka configuration
        kafka_config = {
            'bootstrap.servers': config.broker_url,
            'client.id': f'agent-producer-{config.name}',
            'compression.type': 'lz4',
            'batch.size': 16384,
            'linger.ms': 10,
            'acks': self._get_acks_config(config.delivery_mode),
        }
        
        # Add any extra configuration
        kafka_config.update(config.extra_config or {})
        
        try:
            self._producer = KafkaProducer(kafka_config)
            logger.info(f"Kafka producer initialized for {config.name}")
        except Exception as e:
            raise ConnectionException(f"Failed to create Kafka producer: {e}")
        
        self._delivery_callbacks = {}
    
    def _get_acks_config(self, delivery_mode: DeliveryMode) -> str:
        """Get Kafka acks configuration based on delivery mode."""
        if delivery_mode == DeliveryMode.AT_MOST_ONCE:
            return '0'  # No acknowledgment
        elif delivery_mode == DeliveryMode.AT_LEAST_ONCE:
            return '1'  # Leader acknowledgment
        else:  # EXACTLY_ONCE
            return 'all'  # All replicas acknowledgment
    
    def _delivery_report(self, err, msg):
        """Callback for message delivery reports."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            # Store error for later retrieval if needed
            if msg.key() in self._delivery_callbacks:
                self._delivery_callbacks[msg.key()](err)
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[partition {msg.partition()}] @ offset {msg.offset()}"
            )
    
    def produce(self,
                topic: str,
                value: Any,
                key: Optional[str] = None,
                headers: Optional[Dict[str, str]] = None) -> None:
        """Produce a message to Kafka."""
        try:
            # Serialize the value
            if hasattr(value, 'SerializeToString'):
                # It's a protobuf message
                serialized_value = self.serializer.serialize(value)
            else:
                # Convert to JSON
                serialized_value = json.dumps(value).encode('utf-8')
            
            # Convert headers to list of tuples
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]
            
            # Produce the message
            self._producer.produce(
                topic=topic,
                key=key.encode('utf-8') if key else None,
                value=serialized_value,
                headers=kafka_headers,
                callback=self._delivery_report
            )
            
            # Trigger any pending callbacks
            self._producer.poll(0)
            
        except BufferError:
            # Queue is full, wait and retry
            self._producer.poll(1)
            self.produce(topic, value, key, headers)  # Retry
        except Exception as e:
            raise ProducerException(f"Failed to produce message: {e}")
    
    async def produce_async(self,
                           topic: str,
                           value: Any,
                           key: Optional[str] = None,
                           headers: Optional[Dict[str, str]] = None) -> None:
        """Async version of produce."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.produce, topic, value, key, headers)
    
    def flush(self, timeout: Optional[float] = None) -> None:
        """Flush pending messages."""
        remaining = self._producer.flush(timeout or 10)
        if remaining > 0:
            logger.warning(f"{remaining} messages were not delivered")
    
    def close(self) -> None:
        """Close the producer."""
        self.flush()
        # Kafka producer doesn't have a close method, but we can clean up
        self._delivery_callbacks.clear()
        logger.info("Kafka producer closed")


class KafkaConsumerImpl(Consumer):
    """Kafka implementation of the Consumer interface."""
    
    def __init__(self, config: QueueConfig, topics: List[str]):
        """Initialize Kafka consumer."""
        self.config = config
        self.topics = topics
        self.serializer = MessageSerializer()
        self._running = False
        
        # Build Kafka configuration
        kafka_config = {
            'bootstrap.servers': config.broker_url,
            'group.id': config.consumer_group or f'agent-consumer-{config.name}',
            'client.id': f'agent-consumer-{config.name}',
            'enable.auto.commit': False,  # We'll commit manually
            'auto.offset.reset': 'earliest',
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 60000,  # 1 minute
        }
        
        # Add any extra configuration
        kafka_config.update(config.extra_config or {})
        
        try:
            self._consumer = KafkaConsumer(kafka_config)
            self._consumer.subscribe(topics)
            logger.info(f"Kafka consumer subscribed to topics: {topics}")
        except Exception as e:
            raise ConnectionException(f"Failed to create Kafka consumer: {e}")
    
    def _parse_message(self, kafka_msg) -> Optional[Message]:
        """Parse a Kafka message into our Message format."""
        if kafka_msg.error():
            if kafka_msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition, not an error
                return None
            else:
                raise ConsumerException(f"Kafka error: {kafka_msg.error()}")
        
        # Parse headers
        headers = {}
        if kafka_msg.headers():
            for key, value in kafka_msg.headers():
                headers[key] = value.decode('utf-8') if value else ''
        
        # Deserialize value
        topic = kafka_msg.topic()
        value_bytes = kafka_msg.value()
        
        # Check if we have a registered message type for this topic
        message_class = message_registry.get_message_class(topic)
        if message_class:
            try:
                value = self.serializer.deserialize(value_bytes, message_class)
            except Exception as e:
                logger.error(f"Failed to deserialize protobuf message: {e}")
                # Fallback to raw bytes
                value = value_bytes
        else:
            # Try JSON deserialization
            try:
                value = json.loads(value_bytes.decode('utf-8'))
            except:
                # Keep as bytes if not JSON
                value = value_bytes
        
        return Message(
            topic=topic,
            key=kafka_msg.key().decode('utf-8') if kafka_msg.key() else None,
            value=value,
            headers=headers,
            timestamp=kafka_msg.timestamp()[1] if kafka_msg.timestamp() else None,
            offset=kafka_msg.offset(),
            partition=kafka_msg.partition()
        )
    
    def consume(self,
                handler: MessageHandler,
                timeout: Optional[float] = None) -> None:
        """Consume messages synchronously."""
        self._running = True
        start_time = asyncio.get_event_loop().time() if timeout else None
        
        try:
            while self._running:
                # Check timeout
                if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                    break
                
                # Poll for messages
                kafka_msg = self._consumer.poll(self.config.poll_timeout_ms / 1000)
                
                if kafka_msg is None:
                    continue
                
                # Parse message
                message = self._parse_message(kafka_msg)
                if message is None:
                    continue
                
                # Handle message
                try:
                    handler(message)
                    # Commit on success
                    self._consumer.commit(message=kafka_msg)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    # Don't commit, message will be redelivered
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self._running = False
    
    async def consume_async(self,
                           handler: AsyncMessageHandler,
                           timeout: Optional[float] = None) -> None:
        """Async version of consume."""
        self._running = True
        start_time = asyncio.get_event_loop().time() if timeout else None
        
        try:
            while self._running:
                # Check timeout
                if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                    break
                
                # Poll for messages in executor
                loop = asyncio.get_event_loop()
                kafka_msg = await loop.run_in_executor(
                    None,
                    self._consumer.poll,
                    self.config.poll_timeout_ms / 1000
                )
                
                if kafka_msg is None:
                    continue
                
                # Parse message
                message = self._parse_message(kafka_msg)
                if message is None:
                    continue
                
                # Handle message asynchronously
                try:
                    await handler(message)
                    # Commit on success
                    self._consumer.commit(message=kafka_msg)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    # Don't commit, message will be redelivered
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self._running = False
    
    def commit(self, message: Optional[Message] = None) -> None:
        """Commit message offset."""
        if message:
            # Commit specific message offset
            # This requires the original Kafka message, which we don't have
            # So we'll just commit current position
            logger.warning("Specific message commit not implemented, committing current position")
        
        self._consumer.commit()
    
    def close(self) -> None:
        """Close the consumer."""
        self._running = False
        self._consumer.close()
        logger.info("Kafka consumer closed")
    
    def pause(self, partitions: Optional[List[int]] = None) -> None:
        """Pause consumption."""
        # Get current assignment
        assignment = self._consumer.assignment()
        if partitions:
            # Filter to specific partitions
            to_pause = [tp for tp in assignment if tp.partition in partitions]
        else:
            to_pause = assignment
        
        self._consumer.pause(to_pause)
    
    def resume(self, partitions: Optional[List[int]] = None) -> None:
        """Resume consumption."""
        # Get current assignment
        assignment = self._consumer.assignment()
        if partitions:
            # Filter to specific partitions
            to_resume = [tp for tp in assignment if tp.partition in partitions]
        else:
            to_resume = assignment
        
        self._consumer.resume(to_resume)


class KafkaMessageQueue(MessageQueue):
    """Kafka implementation of MessageQueue."""
    
    def __init__(self, config: QueueConfig):
        """Initialize Kafka message queue."""
        super().__init__(config)
        
        # Create admin client for topic management
        admin_config = {
            'bootstrap.servers': config.broker_url,
            'client.id': f'agent-admin-{config.name}'
        }
        
        try:
            self._admin = AdminClient(admin_config)
            logger.info(f"Kafka message queue initialized: {config.broker_url}")
        except Exception as e:
            raise ConnectionException(f"Failed to create Kafka admin client: {e}")
    
    def create_producer(self) -> Producer:
        """Create a new Kafka producer."""
        return KafkaProducerImpl(self.config)
    
    def create_consumer(self,
                       topics: List[str],
                       group_id: Optional[str] = None) -> Consumer:
        """Create a new Kafka consumer."""
        # Override group_id if provided
        config = self.config
        if group_id:
            config = QueueConfig(**{**config.__dict__, 'consumer_group': group_id})
        
        return KafkaConsumerImpl(config, topics)
    
    def create_topic(self,
                    name: str,
                    partitions: int = 1,
                    replication_factor: int = 1,
                    config: Optional[Dict[str, str]] = None) -> None:
        """Create a new Kafka topic."""
        topic = NewTopic(
            name,
            num_partitions=partitions,
            replication_factor=replication_factor,
            config=config or {}
        )
        
        # Create topic
        fs = self._admin.create_topics([topic])
        
        # Wait for operation to complete
        for topic_name, f in fs.items():
            try:
                f.result()  # The result itself is None
                logger.info(f"Topic {topic_name} created")
            except Exception as e:
                raise TopicException(f"Failed to create topic {topic_name}: {e}")
    
    def delete_topic(self, name: str) -> None:
        """Delete a Kafka topic."""
        fs = self._admin.delete_topics([name])
        
        for topic_name, f in fs.items():
            try:
                f.result()
                logger.info(f"Topic {topic_name} deleted")
            except Exception as e:
                raise TopicException(f"Failed to delete topic {topic_name}: {e}")
    
    def list_topics(self) -> List[str]:
        """List all Kafka topics."""
        metadata = self._admin.list_topics()
        return list(metadata.topics.keys())
    
    def get_topic_metadata(self, topic: str) -> Dict[str, Any]:
        """Get metadata for a Kafka topic."""
        metadata = self._admin.list_topics()
        
        if topic not in metadata.topics:
            raise TopicException(f"Topic {topic} not found")
        
        topic_metadata = metadata.topics[topic]
        return {
            'name': topic,
            'partitions': len(topic_metadata.partitions),
            'error': str(topic_metadata.error) if topic_metadata.error else None
        }
    
    def health_check(self) -> bool:
        """Check if Kafka is healthy."""
        try:
            # Try to list topics as a health check
            self._admin.list_topics(timeout=5)
            return True
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the message queue."""
        # Admin client doesn't need explicit closing
        logger.info("Kafka message queue closed")