"""
Simple event bridge wrapper for testing and integration.

This provides a simpler string-based event API on top of the
typed message system.
"""

import asyncio
from typing import Dict, Any, Callable, List
from dataclasses import dataclass
from datetime import datetime

from .message_bus import MessageBus, Message
from .event_bridge import EventBridge


@dataclass 
class SimpleEvent(Message):
    """Simple event message for string-based events."""
    event_type: str
    event_data: Dict[str, Any]
    
    def __post_init__(self):
        # Set defaults for base Message fields
        if not hasattr(self, 'timestamp'):
            self.timestamp = datetime.now()
        if not hasattr(self, 'source'):
            self.source = 'system'
        if not hasattr(self, 'data'):
            self.data = self.event_data


class SimpleEventBridge:
    """
    Simple event bridge that provides string-based event API.
    
    This wraps the typed message system to provide a simpler
    interface for integration.
    """
    
    def __init__(self, event_bridge: EventBridge = None, message_bus: MessageBus = None):
        """Initialize with existing infrastructure or create new."""
        self.event_bridge = event_bridge
        self.message_bus = message_bus or (event_bridge.message_bus if event_bridge else MessageBus())
        
        # String event handlers
        self._handlers: Dict[str, List[Callable]] = {}
        
        # Subscribe to SimpleEvent messages
        self.message_bus.subscribe(SimpleEvent, self._handle_simple_event)
        
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to string-based events."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from string-based events."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
            
    async def emit(self, event_data: Dict[str, Any]):
        """
        Emit a string-based event.
        
        Args:
            event_data: Dict with 'type' field and other data
        """
        event_type = event_data.get('type', 'unknown')
        
        # Create SimpleEvent message
        event = SimpleEvent(
            event_type=event_type,
            event_data=event_data,
            timestamp=datetime.now(),
            source=event_data.get('source', 'system'),
            data=event_data
        )
        
        # Publish through message bus
        await self.message_bus.publish(event)
        
    async def _handle_simple_event(self, event: SimpleEvent):
        """Handle SimpleEvent messages and dispatch to string handlers."""
        event_type = event.event_type
        
        if event_type in self._handlers:
            # Call all handlers for this event type
            tasks = []
            for handler in self._handlers[event_type]:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event.event_data))
                else:
                    try:
                        handler(event.event_data)
                    except Exception as e:
                        import logging
                        logging.error(f"Error in event handler: {e}")
                        
            # Wait for async handlers
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)