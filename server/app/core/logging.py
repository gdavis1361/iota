"""Logging configuration for the application."""
import logging
import sys
from typing import Optional

from app.core.config import settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with the specified name and level.

    Args:
        name: The name of the logger.
        level: Optional logging level. If not provided, uses DEBUG in development
            and INFO in production.

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)

    # Set default level based on environment if not specified
    if level is None:
        level = "DEBUG" if settings.DEBUG else "INFO"

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper())
    logger.setLevel(numeric_level)

    # Add console handler if no handlers exist
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S.%f",
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
