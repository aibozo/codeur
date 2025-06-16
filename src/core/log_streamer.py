"""
Real-time log streaming for the dashboard.

This module provides logging handlers that stream logs to the dashboard
via WebSocket for real-time monitoring.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import json
import traceback
from contextvars import ContextVar

from src.core.logging import get_logger

# Context variable for tracking agent context
agent_context: ContextVar[Optional[str]] = ContextVar('agent_context', default=None)
job_context: ContextVar[Optional[str]] = ContextVar('job_context', default=None)

logger = get_logger(__name__)


class StreamingLogHandler(logging.Handler):
    """
    Custom log handler that streams logs to WebSocket subscribers.
    
    This handler integrates with the RealtimeService to broadcast
    log entries to connected dashboard clients.
    """
    
    def __init__(self, realtime_service, agent_type: Optional[str] = None,
                 min_level: int = logging.INFO):
        """
        Initialize streaming log handler.
        
        Args:
            realtime_service: Service for WebSocket broadcasting
            agent_type: Optional agent type for filtering
            min_level: Minimum log level to stream
        """
        super().__init__()
        self.realtime_service = realtime_service
        self.agent_type = agent_type
        self.min_level = min_level
        self.setLevel(min_level)
        
        # Set formatter
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record to WebSocket subscribers."""
        try:
            # Skip if below minimum level
            if record.levelno < self.min_level:
                return
                
            # Get context information
            current_agent = agent_context.get() or self.agent_type
            current_job = job_context.get()
            
            # Create log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'source': current_agent or record.name,
                'message': self.format(record),
                'logger_name': record.name,
                'function': record.funcName,
                'line_number': record.lineno,
                'thread': record.thread,
                'thread_name': record.threadName,
                'metadata': {}
            }
            
            # Add context information
            if current_job:
                log_entry['metadata']['job_id'] = current_job
            
            # Add exception information if present
            if record.exc_info:
                log_entry['metadata']['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': traceback.format_exception(*record.exc_info)
                }
            
            # Add extra fields from record
            extra_fields = ['user', 'request_id', 'agent_type', 'task_id', 'metrics']
            for field in extra_fields:
                if hasattr(record, field):
                    log_entry['metadata'][field] = getattr(record, field)
            
            # Don't block on async operation
            asyncio.create_task(self._broadcast_log(log_entry))
            
        except Exception as e:
            # Don't let logging errors break the application
            try:
                self.handleError(record)
            except:
                pass
    
    async def _broadcast_log(self, log_entry: Dict[str, Any]) -> None:
        """Broadcast log entry via WebSocket."""
        try:
            await self.realtime_service.broadcast({
                'type': 'log_entry',
                'timestamp': log_entry['timestamp'],
                'data': log_entry
            }, topic='logs')
        except Exception as e:
            # Log locally if broadcasting fails
            logger.error(f"Failed to broadcast log entry: {e}")


class AgentLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds agent context to log records.
    
    This allows agents to log with their identity automatically included.
    """
    
    def __init__(self, logger: logging.Logger, agent_type: str):
        """
        Initialize agent logger adapter.
        
        Args:
            logger: Base logger instance
            agent_type: Type of agent using this logger
        """
        super().__init__(logger, {'agent_type': agent_type})
        self.agent_type = agent_type
        
    def process(self, msg, kwargs):
        """Add agent context to log records."""
        # Add agent type to extra fields
        extra = kwargs.get('extra', {})
        extra['agent_type'] = self.agent_type
        
        # Add current job if in context
        current_job = job_context.get()
        if current_job:
            extra['job_id'] = current_job
            
        kwargs['extra'] = extra
        return msg, kwargs


def setup_streaming_logs(realtime_service, agent_type: Optional[str] = None,
                        min_level: int = logging.INFO) -> logging.Logger:
    """
    Set up log streaming for an agent or module.
    
    Args:
        realtime_service: RealtimeService instance for broadcasting
        agent_type: Optional agent type for filtering
        min_level: Minimum log level to stream
        
    Returns:
        Logger instance with streaming handler attached
    """
    # Get logger
    logger_name = f"agent.{agent_type}" if agent_type else "agent"
    base_logger = logging.getLogger(logger_name)
    
    # Check if streaming handler already exists
    for handler in base_logger.handlers:
        if isinstance(handler, StreamingLogHandler):
            return base_logger
    
    # Add streaming handler
    handler = StreamingLogHandler(realtime_service, agent_type, min_level)
    base_logger.addHandler(handler)
    
    # Return adapter if agent type specified
    if agent_type:
        return AgentLoggerAdapter(base_logger, agent_type)
    
    return base_logger


class LogContext:
    """Context manager for setting agent and job context."""
    
    def __init__(self, agent_type: Optional[str] = None, 
                 job_id: Optional[str] = None):
        """
        Initialize log context.
        
        Args:
            agent_type: Agent type to set in context
            job_id: Job ID to set in context
        """
        self.agent_type = agent_type
        self.job_id = job_id
        self._agent_token = None
        self._job_token = None
        
    def __enter__(self):
        """Enter context."""
        if self.agent_type:
            self._agent_token = agent_context.set(self.agent_type)
        if self.job_id:
            self._job_token = job_context.set(self.job_id)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self._agent_token:
            agent_context.reset(self._agent_token)
        if self._job_token:
            job_context.reset(self._job_token)


# Structured log entry types
class LogEntryType:
    """Standard log entry types for consistent formatting."""
    
    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    
    # Task execution
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PROGRESS = "task_progress"
    
    # API calls
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_ERROR = "api_error"
    
    # Performance
    PERFORMANCE_METRIC = "performance_metric"
    MEMORY_WARNING = "memory_warning"
    
    # System
    SYSTEM_EVENT = "system_event"
    CONFIG_CHANGE = "config_change"


def log_structured(logger: logging.Logger, level: int, entry_type: str,
                  message: str, **metadata) -> None:
    """
    Log a structured entry with consistent formatting.
    
    Args:
        logger: Logger instance
        level: Log level
        entry_type: Type of log entry (from LogEntryType)
        message: Log message
        **metadata: Additional metadata to include
    """
    extra = {
        'entry_type': entry_type,
        'structured': True,
        **metadata
    }
    
    logger.log(level, message, extra=extra)