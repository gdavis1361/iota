"""
Application bootstrap module.
"""

import logging
from pathlib import Path

import sentry_sdk
import structlog
from dotenv import load_dotenv
from sentry_sdk.integrations.logging import LoggingIntegration

from server.core.config import get_settings
from server.core.sentry import before_send

# Load environment configuration
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
settings = get_settings()


def configure_logging():
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _configure_sentry():
    """Configure Sentry integration with enhanced features."""
    if not settings.SENTRY_ENABLED or not settings.SENTRY_DSN:
        return

    # Configure Sentry logging integration
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)

    # Initialize Sentry with our enhanced configuration
    config = settings.get_sentry_config()
    config.update(
        {
            "integrations": [sentry_logging],
            "before_send": before_send,
        }
    )

    sentry_sdk.init(**config)

    # Add initial metadata
    sentry_sdk.set_context("application", settings.get_sentry_metadata())

    logging.getLogger(__name__).info(
        f"Sentry initialized - Environment: {settings.ENVIRONMENT}, "
        f"Traces Enabled: {settings.SENTRY_TRACES_SAMPLE_RATE > 0}"
    )


def bootstrap_app():
    """Initialize application components."""
    # Configure logging first
    configure_logging()

    # Initialize Sentry with enhanced features
    _configure_sentry()

    # Initialize other components here...

    logging.getLogger(__name__).info(
        f"Application bootstrap complete - "
        f"App: {settings.APP_NAME}, Environment: {settings.ENVIRONMENT}"
    )


# Initialize application on module import
bootstrap_app()
