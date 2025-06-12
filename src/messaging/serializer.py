"""
Message serialization and deserialization for protobuf messages.

This module handles converting between protobuf messages and bytes
for transmission over message queues.
"""

import json
import logging
from typing import Type, TypeVar, Dict, Any, Union, Optional
from google.protobuf.message import Message as ProtobufMessage
from google.protobuf.json_format import MessageToDict, ParseDict
import base64

from .exceptions import SerializationException

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ProtobufMessage)


class MessageSerializer:
    """
    Handles serialization and deserialization of protobuf messages.
    
    Supports multiple serialization formats:
    - Binary protobuf (most efficient)
    - JSON (human-readable, for debugging)
    - Base64-encoded protobuf (for text-only transports)
    """
    
    class Format:
        """Serialization format constants."""
        PROTOBUF = "protobuf"
        JSON = "json"
        BASE64 = "base64"
    
    def __init__(self, format: str = Format.PROTOBUF):
        """
        Initialize the serializer.
        
        Args:
            format: Serialization format to use
        """
        if format not in [self.Format.PROTOBUF, self.Format.JSON, self.Format.BASE64]:
            raise ValueError(f"Invalid format: {format}")
        
        self.format = format
        logger.info(f"MessageSerializer initialized with format: {format}")
    
    def serialize(self, message: ProtobufMessage) -> bytes:
        """
        Serialize a protobuf message to bytes.
        
        Args:
            message: Protobuf message instance
            
        Returns:
            Serialized bytes
            
        Raises:
            SerializationException: If serialization fails
        """
        try:
            if self.format == self.Format.PROTOBUF:
                return message.SerializeToString()
            
            elif self.format == self.Format.JSON:
                # Convert to JSON string then to bytes
                json_dict = MessageToDict(
                    message,
                    preserving_proto_field_name=True,
                    including_default_value_fields=True
                )
                json_str = json.dumps(json_dict, sort_keys=True)
                return json_str.encode('utf-8')
            
            elif self.format == self.Format.BASE64:
                # Serialize to protobuf then base64 encode
                proto_bytes = message.SerializeToString()
                b64_str = base64.b64encode(proto_bytes).decode('ascii')
                return b64_str.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise SerializationException(f"Serialization failed: {e}") from e
    
    def deserialize(self, 
                   data: bytes, 
                   message_class: Type[T]) -> T:
        """
        Deserialize bytes to a protobuf message.
        
        Args:
            data: Serialized bytes
            message_class: Protobuf message class
            
        Returns:
            Deserialized message instance
            
        Raises:
            SerializationException: If deserialization fails
        """
        try:
            message = message_class()
            
            if self.format == self.Format.PROTOBUF:
                message.ParseFromString(data)
                
            elif self.format == self.Format.JSON:
                # Decode JSON and parse into message
                json_str = data.decode('utf-8')
                json_dict = json.loads(json_str)
                ParseDict(json_dict, message)
                
            elif self.format == self.Format.BASE64:
                # Decode base64 then parse protobuf
                b64_str = data.decode('utf-8')
                proto_bytes = base64.b64decode(b64_str)
                message.ParseFromString(proto_bytes)
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            raise SerializationException(f"Deserialization failed: {e}") from e
    
    def serialize_to_dict(self, message: ProtobufMessage) -> Dict[str, Any]:
        """
        Convert a protobuf message to a dictionary.
        
        Useful for logging and debugging.
        
        Args:
            message: Protobuf message instance
            
        Returns:
            Dictionary representation
        """
        return MessageToDict(
            message,
            preserving_proto_field_name=True,
            including_default_value_fields=True
        )
    
    def deserialize_from_dict(self,
                             data: Dict[str, Any],
                             message_class: Type[T]) -> T:
        """
        Create a protobuf message from a dictionary.
        
        Args:
            data: Dictionary data
            message_class: Protobuf message class
            
        Returns:
            Message instance
        """
        message = message_class()
        ParseDict(data, message)
        return message


class MessageTypeRegistry:
    """
    Registry for mapping topic names to protobuf message classes.
    
    This allows automatic deserialization based on topic.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._registry: Dict[str, Type[ProtobufMessage]] = {}
        self._reverse_registry: Dict[Type[ProtobufMessage], str] = {}
    
    def register(self, topic: str, message_class: Type[ProtobufMessage]) -> None:
        """
        Register a message type for a topic.
        
        Args:
            topic: Topic name
            message_class: Protobuf message class
        """
        self._registry[topic] = message_class
        self._reverse_registry[message_class] = topic
        logger.info(f"Registered {message_class.__name__} for topic '{topic}'")
    
    def get_message_class(self, topic: str) -> Optional[Type[ProtobufMessage]]:
        """
        Get the message class for a topic.
        
        Args:
            topic: Topic name
            
        Returns:
            Message class or None if not registered
        """
        return self._registry.get(topic)
    
    def get_topic(self, message_class: Type[ProtobufMessage]) -> Optional[str]:
        """
        Get the topic for a message class.
        
        Args:
            message_class: Protobuf message class
            
        Returns:
            Topic name or None if not registered
        """
        return self._reverse_registry.get(message_class)
    
    def is_registered(self, topic: str) -> bool:
        """Check if a topic is registered."""
        return topic in self._registry
    
    def list_topics(self) -> Dict[str, str]:
        """
        List all registered topics and their message types.
        
        Returns:
            Dictionary of topic -> message class name
        """
        return {
            topic: cls.__name__ 
            for topic, cls in self._registry.items()
        }


# Global registry instance
message_registry = MessageTypeRegistry()


def register_agent_messages():
    """
    Register all agent system message types.
    
    This should be called during application initialization.
    """
    # Import generated protobuf messages
    # This assumes the protos have been compiled
    try:
        from ..proto_gen import messages_pb2
        
        # Register Request Planner messages
        message_registry.register("plan.in", messages_pb2.ChangeRequest)
        message_registry.register("plan.out", messages_pb2.Plan)
        message_registry.register("plan.deadletter", messages_pb2.ChangeRequest)
        
        # Register Code Planner messages
        message_registry.register("code.plan.in", messages_pb2.Plan)
        message_registry.register("code.plan.out", messages_pb2.TaskBundle)
        
        # Register Coding Agent messages
        message_registry.register("coding.task.in", messages_pb2.CodingTask)
        message_registry.register("coding.result.out", messages_pb2.CommitResult)
        
        # Register Build/Test messages
        message_registry.register("build.report", messages_pb2.BuildReport)
        message_registry.register("test.spec.in", messages_pb2.TestSpec)
        
        # Register Verifier messages
        message_registry.register("regression.alert", messages_pb2.Regression)
        
        # Register observability events
        message_registry.register("agent.events", messages_pb2.AgentEvent)
        
        logger.info("Successfully registered all agent message types")
        
    except ImportError as e:
        logger.warning(
            f"Could not import protobuf messages: {e}. "
            "Make sure to run scripts/compile_protos.sh"
        )