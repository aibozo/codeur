"""
Real-time communication infrastructure for the Agent System.

Provides WebSocket management, event streaming, and session persistence.
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect
try:
    import redis.asyncio as redis
except (ImportError, AttributeError):
    # Fallback for older redis versions or when asyncio module not available
    try:
        import aioredis as redis
    except ImportError:
        # If neither works, we'll handle it gracefully
        redis = None

from src.core.logging import get_logger
from src.core.settings import get_settings
from src.core.message_bus import MessageBus, Message

logger = get_logger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""
    AGENT_UPDATE = "agent_update"
    GRAPH_UPDATE = "graph_update"
    LOG_ENTRY = "log_entry"
    JOB_STATUS = "job_status"
    MODEL_CHANGE = "model_change"
    TASK_PROGRESS = "task_progress"
    ERROR = "error"
    
    
@dataclass
class WebSocketMessage:
    """Standard WebSocket message format."""
    type: EventType
    timestamp: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data
        })


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # connection_id -> topics
        self._lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[connection_id] = websocket
            self.subscriptions[connection_id] = set()
            
        logger.info(f"WebSocket connected: {connection_id}")
        
    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.pop(connection_id, None)
            self.subscriptions.pop(connection_id, None)
            
        logger.info(f"WebSocket disconnected: {connection_id}")
        
    async def subscribe(self, connection_id: str, topics: Set[str]) -> None:
        """Subscribe a connection to topics."""
        async with self._lock:
            if connection_id in self.subscriptions:
                self.subscriptions[connection_id].update(topics)
                
    async def unsubscribe(self, connection_id: str, topics: Set[str]) -> None:
        """Unsubscribe a connection from topics."""
        async with self._lock:
            if connection_id in self.subscriptions:
                self.subscriptions[connection_id] -= topics
                
    async def send_message(self, connection_id: str, message: Union[WebSocketMessage, dict]) -> None:
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                if isinstance(message, dict):
                    await websocket.send_json(message)
                else:
                    await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                await self.disconnect(connection_id)
                
    async def broadcast(self, message: WebSocketMessage, topic: Optional[str] = None) -> None:
        """Broadcast a message to all connections or those subscribed to a topic."""
        disconnected = []
        
        for conn_id, websocket in self.active_connections.items():
            # Check topic subscription if specified
            if topic and topic not in self.subscriptions.get(conn_id, set()):
                continue
                
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error broadcasting to {conn_id}: {e}")
                disconnected.append(conn_id)
                
        # Clean up disconnected connections
        for conn_id in disconnected:
            await self.disconnect(conn_id)


class RealtimeService:
    """Service for real-time features including WebSocket and event streaming."""
    
    def __init__(self, message_bus: MessageBus):
        """Initialize realtime service."""
        self.settings = get_settings()
        self.message_bus = message_bus
        self.connection_manager = ConnectionManager()
        self.redis_client: Optional[redis.Redis] = None
        
        # Subscribe to message bus events
        self._setup_message_bus_subscriptions()
        
    async def initialize(self):
        """Initialize Redis connection if configured."""
        if self.settings.cache.redis_url and redis is not None:
            self.redis_client = await redis.from_url(
                self.settings.cache.redis_url,
                decode_responses=True
            )
            logger.info("Redis client initialized for session persistence")
        elif self.settings.cache.redis_url and redis is None:
            logger.warning("Redis URL configured but redis module not available. Session persistence disabled.")
            
    async def shutdown(self):
        """Clean up resources."""
        if self.redis_client:
            await self.redis_client.close()
            
    def _setup_message_bus_subscriptions(self):
        """Subscribe to relevant message bus events for real-time updates."""
        # This will be extended as we integrate with the actual agent system
        pass
        
    async def handle_websocket(self, websocket: WebSocket):
        """Handle a WebSocket connection."""
        connection_id = str(uuid.uuid4())
        heartbeat_task = None
        last_pong_time = datetime.utcnow()
        
        async def heartbeat():
            """Send periodic heartbeat pings and check for pong responses."""
            nonlocal last_pong_time
            while True:
                try:
                    await asyncio.sleep(15)  # Send ping every 15 seconds
                    
                    # Check if we've received a pong recently (within 45 seconds)
                    if (datetime.utcnow() - last_pong_time).total_seconds() > 45:
                        logger.warning(f"No pong received for {connection_id}, closing connection")
                        await websocket.close()
                        break
                    
                    # Send ping
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Heartbeat error for {connection_id}: {e}")
                    break
        
        try:
            await self.connection_manager.connect(websocket, connection_id)
            
            # Send initial connection success
            await websocket.send_json({
                "type": "connection_established",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"status": "connected", "connection_id": connection_id}
            })
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(heartbeat())
            
            # Handle incoming messages
            while True:
                try:
                    # Use receive_text without timeout, rely on heartbeat for connection health
                    data = await websocket.receive_text()
                    
                    # Parse message to check for pong
                    try:
                        message = json.loads(data)
                        if message.get("type") == "pong":
                            last_pong_time = datetime.utcnow()
                    except:
                        pass  # Not JSON or no type field
                    
                    await self._handle_client_message(connection_id, data)
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected normally: {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving message for {connection_id}: {e}")
                    break
                
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            # Clean up
            if heartbeat_task and not heartbeat_task.done():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            await self.connection_manager.disconnect(connection_id)
            
    async def _handle_client_message(self, connection_id: str, data: str):
        """Handle incoming message from client."""
        try:
            message = json.loads(data)
            msg_type = message.get("type")
            
            if msg_type == "subscribe":
                topics = set(message.get("topics", []))
                await self.connection_manager.subscribe(connection_id, topics)
            elif msg_type == "ping":
                # Respond to ping with pong
                websocket = self.connection_manager.active_connections.get(connection_id)
                if websocket:
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
            elif msg_type == "pong":
                # Pong is already handled in the main receive loop
                pass
            elif msg_type == "unsubscribe":
                topics = set(message.get("topics", []))
                await self.connection_manager.unsubscribe(connection_id, topics)
                
            elif msg_type == "command":
                # Handle commands (model changes, etc.)
                await self._handle_command(connection_id, message.get("data", {}))
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await self.connection_manager.send_message(
                connection_id,
                WebSocketMessage(
                    type=EventType.ERROR,
                    timestamp=datetime.utcnow().isoformat(),
                    data={"error": str(e)}
                )
            )
            
    async def _handle_command(self, connection_id: str, command_data: Dict[str, Any]):
        """Handle command from client."""
        command = command_data.get("command")
        
        if command == "set_model":
            # Handle model change request
            agent_type = command_data.get("agent_type")
            model = command_data.get("model")
            
            # This will be implemented when we integrate with settings
            await self.connection_manager.send_message(
                connection_id,
                WebSocketMessage(
                    type=EventType.MODEL_CHANGE,
                    timestamp=datetime.utcnow().isoformat(),
                    data={
                        "agent_type": agent_type,
                        "model": model,
                        "status": "updated"
                    }
                )
            )
            
    # Session persistence methods
    
    async def save_job_state(self, job_id: str, state: Dict[str, Any]) -> None:
        """Save job state to Redis."""
        if not self.redis_client:
            return
            
        key = f"job:{job_id}"
        value = json.dumps({
            **state,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Expire after 24 hours
        await self.redis_client.setex(key, 86400, value)
        
    async def get_job_state(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job state from Redis."""
        if not self.redis_client:
            return None
            
        key = f"job:{job_id}"
        value = await self.redis_client.get(key)
        
        if value:
            return json.loads(value)
        return None
        
    async def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data to Redis."""
        if not self.redis_client:
            return
            
        key = f"session:{session_id}"
        value = json.dumps({
            **session_data,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Expire after 4 hours
        await self.redis_client.setex(key, 14400, value)
        
    async def restore_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Restore session data from Redis."""
        if not self.redis_client:
            return None
            
        key = f"session:{session_id}"
        value = await self.redis_client.get(key)
        
        if value:
            return json.loads(value)
        return None
        
    # Event broadcasting methods
    
    async def broadcast_agent_update(self, agent_type: str, status: str, data: Dict[str, Any]):
        """Broadcast agent status update."""
        message = WebSocketMessage(
            type=EventType.AGENT_UPDATE,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "agent_type": agent_type,
                "status": status,
                **data
            }
        )
        
        await self.connection_manager.broadcast(message, topic="agents")
        
    async def broadcast_log_entry(self, level: str, message: str, source: str):
        """Broadcast log entry."""
        message_obj = WebSocketMessage(
            type=EventType.LOG_ENTRY,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "level": level,
                "message": message,
                "source": source
            }
        )
        
        await self.connection_manager.broadcast(message_obj, topic="logs")
        
    async def broadcast(self, message_data: Dict[str, Any], topic: Optional[str] = None):
        """Broadcast a message to all connected clients or those subscribed to a topic."""
        # Convert dict to WebSocketMessage if needed
        if isinstance(message_data, dict):
            # Check if 'type' is a string and needs to be converted to EventType
            event_type = message_data.get('type', 'message')
            if isinstance(event_type, str):
                # Try to convert string to EventType, default to AGENT_UPDATE for compatibility
                try:
                    event_type = EventType(event_type)
                except ValueError:
                    # Default to AGENT_UPDATE for agent-related messages
                    if event_type in ['agent_update', 'system_metrics', 'queue_metrics']:
                        event_type = EventType.AGENT_UPDATE
                    else:
                        event_type = EventType.ERROR
            
            message = WebSocketMessage(
                type=event_type,
                timestamp=message_data.get('timestamp', datetime.utcnow().isoformat()),
                data=message_data.get('data', {})
            )
        else:
            message = message_data
            
        await self.connection_manager.broadcast(message, topic)
        
    async def broadcast_task_progress(self, task_id: str, progress: float, status: str):
        """Broadcast task progress update."""
        message = WebSocketMessage(
            type=EventType.TASK_PROGRESS,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "task_id": task_id,
                "progress": progress,
                "status": status
            }
        )
        
        await self.connection_manager.broadcast(message, topic="tasks")