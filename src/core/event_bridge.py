"""
Event bridge to connect message bus events to WebSocket streaming.

This module bridges the internal message bus with the real-time
WebSocket infrastructure for frontend updates.
"""

from typing import Dict, Any
from datetime import datetime
from dataclasses import dataclass

from src.core.message_bus import MessageBus, Message
from src.core.realtime import RealtimeService, EventType
from src.core.logging import get_logger
from src.api.models import AgentStatus, JobStatus, LogLevel
from src.core.agent_registry import AgentRegistry
from src.core.flow_tracker import FlowTracker

logger = get_logger(__name__)


# Message types for internal communication

@dataclass
class AgentStatusMessage(Message):
    """Agent status change message."""
    agent_type: str
    status: str
    model: str
    task: str = None


@dataclass 
class TaskProgressMessage(Message):
    """Task progress update message."""
    task_id: str
    progress: float
    status: str
    details: Dict[str, Any] = None


@dataclass
class LogMessage(Message):
    """Log entry message."""
    level: str
    message: str
    source: str
    metadata: Dict[str, Any] = None


@dataclass
class JobUpdateMessage(Message):
    """Job status update message."""
    job_id: str
    title: str
    status: str
    progress: float
    agent_type: str = None


@dataclass
class AgentMessageFlow(Message):
    """Message flow between agents."""
    from_agent: str
    to_agent: str
    message_type: str
    payload_size: int = 0
    duration_ms: int = None
    success: bool = True


class EventBridge:
    """Bridges message bus events to WebSocket real-time updates."""
    
    def __init__(self, message_bus: MessageBus, realtime_service: RealtimeService,
                 agent_registry: AgentRegistry = None, flow_tracker: FlowTracker = None):
        """Initialize event bridge."""
        self.message_bus = message_bus
        self.realtime_service = realtime_service
        self.agent_registry = agent_registry
        self.flow_tracker = flow_tracker
        
        # Subscribe to message bus events
        self._setup_subscriptions()
        
    def _setup_subscriptions(self):
        """Set up message bus subscriptions."""
        # Agent status updates
        self.message_bus.subscribe(
            AgentStatusMessage,
            self._handle_agent_status
        )
        
        # Task progress updates
        self.message_bus.subscribe(
            TaskProgressMessage,
            self._handle_task_progress
        )
        
        # Log messages
        self.message_bus.subscribe(
            LogMessage,
            self._handle_log_message
        )
        
        # Job updates
        self.message_bus.subscribe(
            JobUpdateMessage,
            self._handle_job_update
        )
        
        # Agent message flows
        self.message_bus.subscribe(
            AgentMessageFlow,
            self._handle_message_flow
        )
        
    async def _handle_agent_status(self, message: AgentStatusMessage):
        """Handle agent status change."""
        try:
            # Update registry if available
            if self.agent_registry:
                from src.core.agent_registry import AgentStatus as RegistryStatus
                status_map = {
                    'active': RegistryStatus.ACTIVE,
                    'idle': RegistryStatus.IDLE,
                    'error': RegistryStatus.ERROR,
                    'offline': RegistryStatus.OFFLINE
                }
                registry_status = status_map.get(message.status, RegistryStatus.IDLE)
                await self.agent_registry.update_agent_status(
                    message.agent_type,
                    registry_status,
                    current_task=message.task
                )
            else:
                # Fallback to direct broadcast
                await self.realtime_service.broadcast_agent_update(
                    agent_type=message.agent_type,
                    status=message.status,
                    data={
                        "model": message.model,
                        "task": message.task,
                        "timestamp": message.timestamp.isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Error broadcasting agent status: {e}")
            
    async def _handle_task_progress(self, message: TaskProgressMessage):
        """Handle task progress update."""
        try:
            await self.realtime_service.broadcast_task_progress(
                task_id=message.task_id,
                progress=message.progress,
                status=message.status
            )
            
            # Also save to job state if details provided
            if message.details and "job_id" in message.details:
                await self.realtime_service.save_job_state(
                    message.details["job_id"],
                    {
                        "task_id": message.task_id,
                        "progress": message.progress,
                        "status": message.status,
                        **message.details
                    }
                )
        except Exception as e:
            logger.error(f"Error broadcasting task progress: {e}")
            
    async def _handle_log_message(self, message: LogMessage):
        """Handle log message."""
        try:
            await self.realtime_service.broadcast_log_entry(
                level=message.level,
                message=message.message,
                source=message.source
            )
        except Exception as e:
            logger.error(f"Error broadcasting log message: {e}")
            
    async def _handle_job_update(self, message: JobUpdateMessage):
        """Handle job status update."""
        try:
            # Broadcast the update
            from src.core.realtime import WebSocketMessage
            ws_message = WebSocketMessage(
                type=EventType.JOB_STATUS,
                timestamp=datetime.utcnow().isoformat(),
                data={
                    "job_id": message.job_id,
                    "title": message.title,
                    "status": message.status,
                    "progress": message.progress,
                    "agent_type": message.agent_type
                }
            )
            
            await self.realtime_service.connection_manager.broadcast(
                ws_message,
                topic="jobs"
            )
            
            # Save job state
            await self.realtime_service.save_job_state(
                message.job_id,
                {
                    "job_id": message.job_id,
                    "title": message.title,
                    "status": message.status,
                    "progress": message.progress,
                    "agent_type": message.agent_type,
                    "timestamp": message.timestamp.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling job update: {e}")
    
    async def _handle_message_flow(self, message: AgentMessageFlow):
        """Handle agent message flow."""
        try:
            if self.flow_tracker:
                await self.flow_tracker.track_message(
                    from_agent=message.from_agent,
                    to_agent=message.to_agent,
                    message_type=message.message_type,
                    payload_size=message.payload_size,
                    duration_ms=message.duration_ms,
                    success=message.success
                )
        except Exception as e:
            logger.error(f"Error handling message flow: {e}")


# Helper functions for emitting events

def emit_agent_status(message_bus: MessageBus, agent_type: str, 
                     status: str, model: str, task: str = None):
    """Emit agent status change."""
    message = AgentStatusMessage(
        timestamp=datetime.utcnow(),
        source="agent_system",
        data={},
        agent_type=agent_type,
        status=status,
        model=model,
        task=task
    )
    
    # Use async-aware publish if in async context
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(message_bus.publish(message))
    except RuntimeError:
        # Not in async context, use sync publish
        message_bus.publish_sync(message)


def emit_task_progress(message_bus: MessageBus, task_id: str,
                      progress: float, status: str, **kwargs):
    """Emit task progress update."""
    message = TaskProgressMessage(
        timestamp=datetime.utcnow(),
        source="task_executor",
        data={},
        task_id=task_id,
        progress=progress,
        status=status,
        details=kwargs
    )
    
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(message_bus.publish(message))
    except RuntimeError:
        message_bus.publish_sync(message)


def emit_log(message_bus: MessageBus, level: str, message: str, 
             source: str, **metadata):
    """Emit log message."""
    log_message = LogMessage(
        timestamp=datetime.utcnow(),
        source=source,
        data={},
        level=level,
        message=message,
        metadata=metadata
    )
    
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(message_bus.publish(log_message))
    except RuntimeError:
        message_bus.publish_sync(log_message)


def emit_job_update(message_bus: MessageBus, job_id: str, title: str,
                   status: str, progress: float, agent_type: str = None):
    """Emit job status update."""
    message = JobUpdateMessage(
        timestamp=datetime.utcnow(),
        source="job_manager",
        data={},
        job_id=job_id,
        title=title,
        status=status,
        progress=progress,
        agent_type=agent_type
    )
    
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(message_bus.publish(message))
    except RuntimeError:
        message_bus.publish_sync(message)