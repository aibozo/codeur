"""
Logging configuration for the agent system with structured logging support.
"""

import logging
import logging.handlers
import sys
import json
import uuid
import contextvars
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Module-level flag to track if logging has been initialized
_logging_initialized = False

# Context variables for request tracking
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'request_id', default=None
)
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request/correlation IDs if available
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data['correlation_id'] = correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'exc_info',
                          'exc_text', 'stack_info', 'pathname', 'processName',
                          'process', 'threadName', 'thread', 'getMessage']:
                log_data[key] = value
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Enhanced console formatter with request ID support."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        # Add request ID to the record if available
        request_id = request_id_var.get()
        if request_id:
            record.request_id = f"[{request_id[:8]}]"
        else:
            record.request_id = ""
        
        return super().format(record)


def setup_logging(level=logging.INFO, force_reinit=False, structured=True):
    """
    Configure logging for the agent system.
    
    Args:
        level: Logging level (default: INFO)
        force_reinit: Force re-initialization of logging (default: False)
        structured: Use structured JSON logging (default: True)
    """
    global _logging_initialized
    
    # Skip if already initialized unless forced
    if _logging_initialized and not force_reinit:
        return logging.getLogger()
    
    # Import settings here to avoid circular imports
    from src.core.settings import get_settings
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = settings.logging.log_dir
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()
    
    root_logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(
        getattr(logging, settings.logging.console_log_level.upper())
    )
    
    if structured and settings.logging.log_format in ['structured', 'json']:
        console_formatter = StructuredFormatter()
    else:
        console_format = ConsoleFormatter(
            '%(asctime)s %(request_id)s %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_formatter = console_format
    
    console_handler.setFormatter(console_formatter)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / settings.logging.log_file_name,
        maxBytes=settings.logging.max_log_size_mb * 1024 * 1024,
        backupCount=settings.logging.backup_count
    )
    file_handler.setLevel(
        getattr(logging, settings.logging.file_log_level.upper())
    )
    
    if settings.logging.log_format in ['structured', 'json']:
        file_formatter = StructuredFormatter()
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
    
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Mark as initialized
    _logging_initialized = True
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID for the current context."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return request_id_var.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set the correlation ID for the current context."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def log_with_context(logger: logging.Logger, level: int, message: str, 
                    extra: Optional[Dict[str, Any]] = None):
    """Log a message with additional context."""
    if extra is None:
        extra = {}
    
    # Add any context-specific data
    extra['request_id'] = get_request_id()
    extra['correlation_id'] = get_correlation_id()
    
    logger.log(level, message, extra=extra)