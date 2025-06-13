"""
Simple message bus implementation for the web API.
This provides a basic pub/sub mechanism for system events.
"""

from typing import Dict, List, Callable, Any, Type
import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageBus:
    """
    Simple in-memory message bus for pub/sub communication.
    
    This is a basic implementation to support the web API.
    For production use, consider using the full messaging system
    with Kafka or RabbitMQ support from src.messaging.
    """
    
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = defaultdict(list)
        self._async_subscribers: Dict[Type, List[Callable]] = defaultdict(list)
        
    def subscribe(self, message_type: Type, handler: Callable) -> None:
        """
        Subscribe to a message type.
        
        Args:
            message_type: The protobuf message class to subscribe to
            handler: Callback function to handle the message
        """
        if asyncio.iscoroutinefunction(handler):
            self._async_subscribers[message_type].append(handler)
        else:
            self._subscribers[message_type].append(handler)
        
        logger.debug(f"Subscribed handler {handler.__name__} to {message_type.__name__}")
    
    def unsubscribe(self, message_type: Type, handler: Callable) -> None:
        """
        Unsubscribe from a message type.
        
        Args:
            message_type: The protobuf message class to unsubscribe from
            handler: The handler to remove
        """
        if handler in self._subscribers[message_type]:
            self._subscribers[message_type].remove(handler)
        if handler in self._async_subscribers[message_type]:
            self._async_subscribers[message_type].remove(handler)
            
        logger.debug(f"Unsubscribed handler {handler.__name__} from {message_type.__name__}")
    
    async def publish_async(self, message: Any) -> None:
        """
        Publish a message asynchronously.
        
        Args:
            message: The protobuf message to publish
        """
        message_type = type(message)
        
        # Call sync handlers
        for handler in self._subscribers[message_type]:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in sync handler {handler.__name__}: {e}")
        
        # Call async handlers
        tasks = []
        for handler in self._async_subscribers[message_type]:
            try:
                tasks.append(asyncio.create_task(handler(message)))
            except Exception as e:
                logger.error(f"Error in async handler {handler.__name__}: {e}")
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def publish(self, message: Any) -> None:
        """
        Publish a message synchronously.
        
        Args:
            message: The protobuf message to publish
        """
        message_type = type(message)
        
        for handler in self._subscribers[message_type]:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}")
        
        # For async handlers, we need to run them in the event loop
        if self._async_subscribers[message_type]:
            logger.warning(
                f"Async handlers registered for {message_type.__name__} "
                "but publish() called synchronously. Use publish_async() instead."
            )
    
    def clear(self) -> None:
        """Clear all subscriptions."""
        self._subscribers.clear()
        self._async_subscribers.clear()