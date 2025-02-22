"""
Configuration management for the application.

This module provides centralized configuration management using Pydantic.
It handles environment variables, validation, and type conversion.
"""

import json
import os
import secrets
from functools import lru_cache
from typing import Optional

from .base import EndpointLimit, EnvironmentType, RateLimitConfig, Settings

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = create_settings()
    return _settings


def initialize_settings() -> Settings:
    """Initialize settings for the first time."""
    global _settings
    _settings = create_settings()
    return _settings


def create_settings() -> Settings:
    """Create settings based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()

    # Handle test environment
    if env in ("test", "testing"):
        return create_test_settings()

    # For other environments, ensure required variables are set
    if not os.getenv("SECRET_KEY"):
        os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)

    if not os.getenv("POSTGRES_PASSWORD"):
        raise ValueError("POSTGRES_PASSWORD must be set for non-test environments")

    if not os.getenv("POSTGRES_DB"):
        raise ValueError("POSTGRES_DB must be set for non-test environments")

    return Settings()


def create_test_settings() -> Settings:
    """Create test settings with safe defaults."""
    # Set test environment variables if not already set
    test_env_vars = {
        "ENVIRONMENT": EnvironmentType.TESTING.value,  # Use enum value
        "SECRET_KEY": os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "test_password"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "test_db"),
        "DEBUG": os.getenv("DEBUG", "true"),
        "ALLOWED_HOSTS": os.getenv("ALLOWED_HOSTS", json.dumps(["*"])),
        "SAMPLING_WINDOW_SECONDS": os.getenv("SAMPLING_WINDOW_SECONDS", "60"),
        "SLOW_REQUEST_THRESHOLD_MS": os.getenv("SLOW_REQUEST_THRESHOLD_MS", "500"),
        "ERROR_RATE_THRESHOLD": os.getenv("ERROR_RATE_THRESHOLD", "0.2"),
        "SLOW_RATE_THRESHOLD": os.getenv("SLOW_RATE_THRESHOLD", "0.2"),
    }

    # Update environment with test values
    for key, value in test_env_vars.items():
        if key not in os.environ:
            os.environ[key] = str(value)  # Ensure all values are strings

    return Settings()


__all__ = [
    "Settings",
    "get_settings",
    "initialize_settings",
    "EndpointLimit",
    "RateLimitConfig",
    "EnvironmentType",
]
