"""Centralized logging configuration for IOTA."""

import logging
import sys
from enum import Enum
from typing import Optional


class LogLevel(str, Enum):
    """Log levels supported by the logging system."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ColorFormatter(logging.Formatter):
    """Custom formatter adding colors to log levels."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(
    name: Optional[str] = None, level: LogLevel = LogLevel.INFO, log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting and optional file output.

    Args:
        name: Logger name. If None, returns root logger
        level: Logging level to use
        log_file: Optional file path to write logs to

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Convert LogLevel enum to string
    level_str = level.value if isinstance(level, LogLevel) else level
    logger.setLevel(level_str)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler with color formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


# Example usage:
# logger = setup_logger("iota.scripts", LogLevel.DEBUG, "iota.log")
