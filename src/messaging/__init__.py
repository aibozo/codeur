"""
Message queue infrastructure for the agent system.

This package provides:
- Abstract message queue interfaces
- Kafka and AMQP implementations
- Message serialization/deserialization
- Dead letter queue handling
- Configuration management
"""

from .base import (
    MessageQueue,
    Producer,
    Consumer,
    Message,
    MessageHandler,
    QueueConfig
)
from .serializer import MessageSerializer
from .exceptions import (
    MessagingException,
    ProducerException,
    ConsumerException,
    SerializationException
)
# Import implementations with graceful fallback
try:
    from .kafka_impl import KafkaMessageQueue
except ImportError:
    KafkaMessageQueue = None

from .memory_impl import InMemoryMessageQueue
from .config import MessagingConfig, get_config, load_config_from_file
from .factory import create_message_queue

__all__ = [
    'MessageQueue',
    'Producer',
    'Consumer',
    'Message',
    'MessageHandler',
    'QueueConfig',
    'MessageSerializer',
    'MessagingException',
    'ProducerException',
    'ConsumerException',
    'SerializationException',
    'KafkaMessageQueue',
    'InMemoryMessageQueue',
    'MessagingConfig',
    'get_config',
    'load_config_from_file',
    'create_message_queue',
]