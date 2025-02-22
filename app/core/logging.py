"""Logging configuration."""
from typing import Any, Dict

import structlog


def setup_logging() -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_route_info(route: Any) -> Dict[str, Any]:
    """Extract relevant information from a route."""
    return {
        "path": route.path,
        "name": route.name,
        "methods": list(route.methods) if route.methods else [],
        "endpoint": route.endpoint.__name__
        if hasattr(route.endpoint, "__name__")
        else str(route.endpoint),
        "tags": getattr(route, "tags", []),
    }
