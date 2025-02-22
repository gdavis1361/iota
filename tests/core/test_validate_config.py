import pytest
from pydantic import ValidationError

from server.core.config import Settings


def test_environment_validation():
    """Test environment validation."""
    # Valid environments
    Settings(SECRET_KEY="x" * 32, ENVIRONMENT="development")
    Settings(SECRET_KEY="x" * 32, ENVIRONMENT="production", ALLOWED_HOSTS=["example.com"])
    Settings(SECRET_KEY="x" * 32, ENVIRONMENT="staging")
    Settings(SECRET_KEY="x" * 32, ENVIRONMENT="test")

    # Invalid environment
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="x" * 32, ENVIRONMENT="invalid")
    assert "Invalid environment" in str(exc_info.value)


def test_secret_key_validation():
    """Test SECRET_KEY validation."""
    # Valid secret key
    Settings(SECRET_KEY="x" * 32)

    # Invalid secret key (too short)
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="short")
    assert "SECRET_KEY must be at least 32 characters long" in str(exc_info.value)


def test_sentry_validation():
    """Test Sentry configuration validation."""
    valid_dsn = "https://key@sentry.example.com/123"

    # Valid config with Sentry enabled
    Settings(SECRET_KEY="x" * 32, SENTRY_ENABLED=True, SENTRY_DSN=valid_dsn)

    # Invalid DSN format
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="x" * 32, SENTRY_ENABLED=True, SENTRY_DSN="invalid-dsn")
    assert "Invalid Sentry DSN format" in str(exc_info.value)


def test_allowed_hosts_validation():
    """Test ALLOWED_HOSTS validation."""
    # Valid in development
    Settings(SECRET_KEY="x" * 32, ENVIRONMENT="development", ALLOWED_HOSTS=["*"])

    # Invalid in production
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="x" * 32, ENVIRONMENT="production", ALLOWED_HOSTS=["*"])
    assert "Wildcard (*) not allowed in ALLOWED_HOSTS in production" in str(exc_info.value)


def test_rate_validation():
    """Test rate value validation."""
    # Valid rates
    Settings(SECRET_KEY="x" * 32, SENTRY_TRACES_SAMPLE_RATE=0.5, ERROR_RATE_THRESHOLD=0.1)

    # Invalid rates
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="x" * 32, SENTRY_TRACES_SAMPLE_RATE=1.5)
    assert "must be between 0 and 1" in str(exc_info.value)


def test_log_level_validation():
    """Test LOG_LEVEL validation."""
    # Valid levels
    Settings(SECRET_KEY="x" * 32, LOG_LEVEL="DEBUG")
    Settings(SECRET_KEY="x" * 32, LOG_LEVEL="INFO")
    Settings(SECRET_KEY="x" * 32, LOG_LEVEL="WARNING")
    Settings(SECRET_KEY="x" * 32, LOG_LEVEL="ERROR")
    Settings(SECRET_KEY="x" * 32, LOG_LEVEL="CRITICAL")

    # Invalid level
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="x" * 32, LOG_LEVEL="INVALID")
    assert "Invalid log level" in str(exc_info.value)


def test_log_format_validation():
    """Test LOG_FORMAT validation."""
    # Valid formats
    Settings(SECRET_KEY="x" * 32, LOG_FORMAT="json")
    Settings(SECRET_KEY="x" * 32, LOG_FORMAT="console")

    # Invalid format
    with pytest.raises(ValidationError) as exc_info:
        Settings(SECRET_KEY="x" * 32, LOG_FORMAT="invalid")
    assert "Invalid log format" in str(exc_info.value)
