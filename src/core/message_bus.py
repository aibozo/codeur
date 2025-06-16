"""
Simple message bus implementation for the Agent System.

This provides basic pub/sub functionality for system events.
"""

from typing import Dict, List, Callable, Any, Type
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Base message class."""
    timestamp: datetime
    source: str
    data: Dict[str, Any]


class MessageBus:
    """Simple message bus for pub/sub communication."""
    
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = {}
        self._async_subscribers: Dict[Type, List[Callable]] = {}
        self._lock = asyncio.Lock()
        # Support for wildcard subscriptions (for testing)
        self._wildcard_subscribers: List[Callable] = []
        self._async_wildcard_subscribers: List[Callable] = []
        
    def subscribe(self, message_type: Type, handler: Callable) -> None:
        """Subscribe to a message type with a handler."""
        # Handle wildcard subscription
        if message_type == "*":
            if asyncio.iscoroutinefunction(handler):
                self._async_wildcard_subscribers.append(handler)
            else:
                self._wildcard_subscribers.append(handler)
            # Also add to regular subscribers for compatibility
            if "*" not in self._subscribers:
                self._subscribers["*"] = []
            self._subscribers["*"].append(handler)
            return
            
        if asyncio.iscoroutinefunction(handler):
            if message_type not in self._async_subscribers:
                self._async_subscribers[message_type] = []
            self._async_subscribers[message_type].append(handler)
        else:
            if message_type not in self._subscribers:
                self._subscribers[message_type] = []
            self._subscribers[message_type].append(handler)
            
    def unsubscribe(self, message_type: Type, handler: Callable) -> None:
        """Unsubscribe a handler from a message type."""
        if message_type in self._subscribers:
            self._subscribers[message_type] = [
                h for h in self._subscribers[message_type] if h != handler
            ]
        if message_type in self._async_subscribers:
            self._async_subscribers[message_type] = [
                h for h in self._async_subscribers[message_type] if h != handler
            ]
            
    async def publish(self, message: Any) -> None:
        """Publish a message to all subscribers."""
        message_type = type(message)
        
        # Handle wildcard subscribers first (for testing)
        # Extract event type and data if this is a dict-like message
        if hasattr(message, '__dict__') or isinstance(message, dict):
            if isinstance(message, dict):
                event_type = message.get('type', str(message_type))
                event_data = message.get('data', message)
            else:
                event_type = getattr(message, 'type', str(message_type))
                event_data = getattr(message, 'data', message.__dict__)
                
            # Notify wildcard subscribers
            for handler in self._wildcard_subscribers:
                try:
                    handler(event_type, event_data)
                except Exception as e:
                    logger.error(f"Error in wildcard handler: {e}")
                    
            # Handle async wildcard subscribers
            wildcard_tasks = []
            for handler in self._async_wildcard_subscribers:
                try:
                    wildcard_tasks.append(handler(event_type, event_data))
                except Exception as e:
                    logger.error(f"Error in async wildcard handler: {e}")
                    
            if wildcard_tasks:
                await asyncio.gather(*wildcard_tasks, return_exceptions=True)
        
        # Handle sync subscribers
        if message_type in self._subscribers:
            for handler in self._subscribers[message_type]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
                    
        # Handle async subscribers
        if message_type in self._async_subscribers:
            tasks = []
            for handler in self._async_subscribers[message_type]:
                try:
                    tasks.append(handler(message))
                except Exception as e:
                    logger.error(f"Error in async message handler: {e}")
                    
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
    def publish_sync(self, message: Any) -> None:
        """Synchronous publish for non-async contexts."""
        message_type = type(message)
        
        if message_type in self._subscribers:
            for handler in self._subscribers[message_type]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")