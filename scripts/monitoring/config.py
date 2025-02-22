"""
Configuration module for the IOTA monitoring system.
Contains alert thresholds and monitoring settings.
"""

import os
from typing import Any, Dict


def _get_env_float(key: str, default: float) -> float:
    """Get a float value from environment variable with fallback."""
    value = os.getenv(key)
    return float(value) if value is not None else default


def _get_env_int(key: str, default: int) -> int:
    """Get an integer value from environment variable with fallback."""
    value = os.getenv(key)
    return int(value) if value is not None else default


# Alert thresholds with environment variable overrides
ALERT_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "latency": {
        "warning": _get_env_float("LATENCY_WARNING_MS", 1.0),  # milliseconds
        "critical": _get_env_float("LATENCY_CRITICAL_MS", 2.0),
    },
    "memory": {
        "warning": _get_env_int("MEMORY_WARNING_MB", 750),  # megabytes
        "critical": _get_env_int("MEMORY_CRITICAL_MB", 1000),
    },
    "rejection_rate": {
        "warning": _get_env_float("REJECTION_WARNING_PERCENT", 10.0),  # percentage
        "critical": _get_env_float("REJECTION_CRITICAL_PERCENT", 20.0),
    },
    "redis_errors": {
        "warning": _get_env_int("REDIS_WARNING_ERRORS", 0),  # errors per minute
        "critical": _get_env_int("REDIS_CRITICAL_ERRORS", 1),
    },
}

# Metric collection settings
METRIC_COLLECTION = {
    "interval_minutes": _get_env_int("METRIC_INTERVAL_MINUTES", 5),
    "query_timeout_seconds": _get_env_int("METRIC_QUERY_TIMEOUT_SECONDS", 30),
    "retention_days": _get_env_int("METRIC_RETENTION_DAYS", 30),
    "resolution_minutes": {
        "recent": _get_env_int("METRIC_RESOLUTION_RECENT_MINUTES", 1),  # Last 24h
        "historical": _get_env_int("METRIC_RESOLUTION_HISTORICAL_MINUTES", 5),  # Older data
    },
}

# Alert routing configuration
ALERT_ROUTING = {
    "critical": {
        "primary": "pagerduty",
        "secondary": "slack",
        "channel": "#incidents",
        "repeat_interval_hours": _get_env_int("CRITICAL_ALERT_REPEAT_HOURS", 1),
        "auto_resolve_hours": _get_env_int("CRITICAL_ALERT_RESOLVE_HOURS", 24),
    },
    "warning": {
        "primary": "slack",
        "secondary": "ticket",
        "channel": "#iota-alerts",
        "repeat_interval_hours": _get_env_int("WARNING_ALERT_REPEAT_HOURS", 4),
        "auto_resolve_hours": _get_env_int("WARNING_ALERT_RESOLVE_HOURS", 168),  # 7 days
    },
}

# Alert grouping settings
ALERT_GROUPING = {
    "wait_period_seconds": _get_env_int("ALERT_GROUP_WAIT_SECONDS", 30),
    "group_interval_minutes": _get_env_int("ALERT_GROUP_INTERVAL_MINUTES", 5),
}
