"""
Logging configuration for the agent system.
"""

import logging
import sys
from pathlib import Path

# Module-level flag to track if logging has been initialized
_logging_initialized = False


def setup_logging(level=logging.INFO, force_reinit=False):
    """
    Configure logging for the agent system.
    
    Args:
        level: Logging level (default: INFO)
        force_reinit: Force re-initialization of logging (default: False)
    """
    global _logging_initialized
    
    # Skip if already initialized unless forced
    if _logging_initialized and not force_reinit:
        return logging.getLogger()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()
    
    root_logger.setLevel(level)
    
    # Console handler with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # File handler with detailed format
    file_handler = logging.FileHandler(log_dir / "agent.log")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Mark as initialized
    _logging_initialized = True
    
    return root_logger