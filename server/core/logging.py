"""
Structured logging configuration with support for both JSON and console formats.
"""
import sys
import logging
import structlog
from typing import Optional
from pythonjsonlogger import jsonlogger
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

from .config import get_settings

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    try:
        return correlation_id.get()
    except LookupError:
        return str(uuid4())

@contextmanager
def correlation_id_context(corr_id: Optional[str] = None):
    """Context manager for setting correlation ID."""
    token = correlation_id.set(corr_id or str(uuid4()))
    try:
        yield
    finally:
        correlation_id.reset(token)

def setup_logging():
    """Configure structured logging based on settings."""
    settings = get_settings()
    
    # Set logging level
    level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Common processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add correlation ID processor
    def add_correlation_id(logger, method_name, event_dict):
        event_dict['correlation_id'] = get_correlation_id()
        return event_dict
    
    processors.append(add_correlation_id)
    
    # Configure format-specific processors
    if settings.LOG_FORMAT.lower() == 'json':
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging to use JSON format if specified
    if settings.LOG_FORMAT.lower() == 'json':
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(
            jsonlogger.JsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
        )
        logging.basicConfig(
            level=level,
            handlers=[json_handler]
        )
    else:
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    
    # Set log file if specified
    if settings.LOG_FILE_PATH:
        file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
        if settings.LOG_FORMAT.lower() == 'json':
            file_handler.setFormatter(
                jsonlogger.JsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
            )
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
            )
        logging.getLogger().addHandler(file_handler)

# Create a logger instance
logger = structlog.get_logger()
