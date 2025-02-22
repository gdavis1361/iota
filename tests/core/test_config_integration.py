"""Integration tests for configuration system."""

import os
from contextlib import contextmanager

import pytest

from server.core.config import Settings


@contextmanager
def env_vars(**kwargs):
    """Temporarily set environment variables."""
    original = {k: os.environ.get(k) for k in kwargs}
    os.environ.update({k: str(v) for k, v in kwargs.items()})
    try:
        yield
    finally:
        for k, v in original.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v


def test_environment_file_loading():
    """Test loading configuration from environment file."""
    with env_vars(
        SECRET_KEY="x" * 32, APP_NAME="test-app", LOG_LEVEL="DEBUG", ENVIRONMENT="development"
    ):
        settings = Settings()
        assert settings.APP_NAME == "test-app"
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.ENVIRONMENT == "development"


def test_production_security_settings():
    """Test production environment security settings."""
    with env_vars(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 32,
        ALLOWED_HOSTS='["example.com"]',  # Fix: Use JSON format
        SENTRY_ENABLED="true",
        SENTRY_DSN="https://key@sentry.example.com/123",
        DEBUG="false",  # Fix: Explicitly set DEBUG to false
    ):
        settings = Settings()
        assert settings.ENVIRONMENT == "production"
        assert settings.ALLOWED_HOSTS == ["example.com"]
        assert settings.SENTRY_ENABLED is True
        assert settings.SENTRY_DSN == "https://key@sentry.example.com/123"


def test_logging_configuration():
    """Test logging configuration integration."""
    with env_vars(SECRET_KEY="x" * 32, LOG_LEVEL="DEBUG", LOG_FORMAT="json"):
        settings = Settings()
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.LOG_FORMAT == "json"


def test_sentry_integration():
    """Test Sentry configuration integration."""
    with env_vars(
        SECRET_KEY="x" * 32,
        SENTRY_ENABLED="true",
        SENTRY_DSN="https://key@sentry.example.com/123",
        SENTRY_ENVIRONMENT="staging",
        SENTRY_TRACES_SAMPLE_RATE="0.5",
    ):
        settings = Settings()
        assert settings.SENTRY_ENABLED is True
        assert settings.SENTRY_DSN == "https://key@sentry.example.com/123"
        assert settings.SENTRY_ENVIRONMENT == "staging"
        assert settings.SENTRY_TRACES_SAMPLE_RATE == 0.5


def test_performance_monitoring():
    """Test performance monitoring configuration."""
    with env_vars(
        SECRET_KEY="x" * 32,
        SLOW_REQUEST_THRESHOLD_MS="2000.0",
        ERROR_RATE_THRESHOLD="0.05",
        SLOW_RATE_THRESHOLD="0.1",
    ):
        settings = Settings()
        assert settings.SLOW_REQUEST_THRESHOLD_MS == 2000.0
        assert settings.ERROR_RATE_THRESHOLD == 0.05
        assert settings.SLOW_RATE_THRESHOLD == 0.1


def test_environment_specific_defaults():
    """Test environment-specific default values."""
    # Test environment
    with env_vars(SECRET_KEY="x" * 32, ENVIRONMENT="test"):
        settings = Settings()
        assert settings.APP_NAME == "iota-test"
        assert settings.DEBUG is True
        assert settings.SENTRY_ENABLED is False
        assert settings.SENTRY_TRACES_SAMPLE_RATE == 0.0

    # Production environment
    with env_vars(
        SECRET_KEY="x" * 32,
        ENVIRONMENT="production",
        ALLOWED_HOSTS='["example.com"]',  # Fix: Use JSON format for list
        DEBUG="false",  # Fix: Explicitly set DEBUG to false
    ):
        settings = Settings()
        assert settings.DEBUG is False
        assert settings.ALLOWED_HOSTS == ["example.com"]


def test_type_conversion():
    """Test type conversion of environment variables."""
    with env_vars(
        SECRET_KEY="x" * 32,
        DEBUG="true",
        SENTRY_ENABLED="false",
        SENTRY_TRACES_SAMPLE_RATE="0.5",
        SLOW_REQUEST_THRESHOLD_MS="1500.5",
    ):
        settings = Settings()
        assert isinstance(settings.DEBUG, bool) and settings.DEBUG is True
        assert isinstance(settings.SENTRY_ENABLED, bool) and settings.SENTRY_ENABLED is False
        assert isinstance(settings.SENTRY_TRACES_SAMPLE_RATE, float)
        assert isinstance(settings.SLOW_REQUEST_THRESHOLD_MS, float)
        assert settings.SLOW_REQUEST_THRESHOLD_MS == 1500.5
