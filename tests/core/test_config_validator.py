"""Tests for the configuration validator."""

import os
from pathlib import Path

import pytest

from scripts.validate_config import ConfigurationValidator


@pytest.fixture
def validator():
    """Create a fresh validator instance for each test."""
    return ConfigurationValidator()


@pytest.fixture
def test_env():
    """Set up test environment variables."""
    original_env = dict(os.environ)

    # Set test environment variables with valid format
    test_vars = {
        "ENVIRONMENT": "test",
        "SECRET_KEY": "x" * 32,  # 32-character test key
        "SENTRY_ENABLED": "true",
        "SENTRY_DSN": "https://abc123@o123456.ingest.sentry.io/123456",  # Valid format
        "ALLOWED_HOSTS": '["test.com"]',
        "DEBUG": "false",
    }
    os.environ.update(test_vars)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


def test_validator_initialization(validator):
    """Test validator initializes correctly."""
    assert validator.issues["errors"] == []
    assert validator.issues["warnings"] == []
    assert validator.issues["security_concerns"] == []


def test_secret_key_length(validator, test_env):
    """Test SECRET_KEY length validation."""
    # Test with short key
    os.environ["SECRET_KEY"] = "short"
    assert not validator._validate_security_settings()
    assert any("SECRET_KEY is too short" in msg for msg in validator.issues["security_concerns"])

    # Test with proper length key
    os.environ["SECRET_KEY"] = "x" * 32
    validator.issues["security_concerns"] = []
    assert validator._validate_security_settings()
    assert not validator.issues["security_concerns"]


def test_environment_validation(validator, test_env):
    """Test environment validation."""
    # Test valid environments
    for env in ["development", "staging", "production", "test"]:
        os.environ["ENVIRONMENT"] = env
        validator.issues["errors"] = []
        assert validator._validate_environment()
        assert not validator.issues["errors"]

    # Test invalid environment
    os.environ["ENVIRONMENT"] = "invalid"
    assert not validator._validate_environment()
    assert any("Invalid ENVIRONMENT value" in msg for msg in validator.issues["errors"])


def test_production_debug_check(validator, test_env):
    """Test DEBUG setting in production environment."""
    os.environ["ENVIRONMENT"] = "production"

    # Test DEBUG=True in production (should fail)
    os.environ["DEBUG"] = "true"
    assert not validator._validate_environment()
    assert any(
        "DEBUG should not be enabled in production" in msg
        for msg in validator.issues["security_concerns"]
    )

    # Test DEBUG=False in production (should pass)
    os.environ["DEBUG"] = "false"
    validator.issues["security_concerns"] = []
    assert validator._validate_environment()
    assert not validator.issues["security_concerns"]


def test_sentry_validation(validator, test_env):
    """Test Sentry configuration validation."""
    # Test missing DSN when Sentry is enabled
    os.environ["SENTRY_ENABLED"] = "true"
    os.environ.pop("SENTRY_DSN", None)
    assert not validator._validate_sentry_config()
    assert any("SENTRY_DSN is required" in msg for msg in validator.issues["errors"])

    # Test invalid DSN format
    os.environ["SENTRY_DSN"] = "invalid-dsn"
    validator.issues["errors"] = []
    assert not validator._validate_sentry_config()
    assert any("SENTRY_DSN must start with http://" in msg for msg in validator.issues["errors"])

    # Test valid Sentry configuration
    os.environ["SENTRY_DSN"] = "https://abc123@o123456.ingest.sentry.io/123456"
    validator.issues["errors"] = []
    assert validator._validate_sentry_config()
    assert not validator.issues["errors"]


def test_allowed_hosts_validation(validator, test_env):
    """Test allowed hosts validation."""
    # Test wildcard in production (should fail)
    os.environ["ENVIRONMENT"] = "production"
    os.environ["ALLOWED_HOSTS"] = '["*"]'
    assert not validator._validate_allowed_hosts()
    assert any(
        "Wildcard ALLOWED_HOSTS should not be used in production" in msg
        for msg in validator.issues["security_concerns"]
    )

    # Test specific hosts in production (should pass)
    os.environ["ALLOWED_HOSTS"] = '["test.com", "api.test.com"]'
    validator.issues["security_concerns"] = []
    assert validator._validate_allowed_hosts()
    assert not validator.issues["security_concerns"]


def test_full_validation_success(validator, test_env):
    """Test full validation with valid configuration."""
    os.environ.update(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "x" * 32,
            "DEBUG": "false",
            "SENTRY_ENABLED": "true",
            "SENTRY_DSN": "https://abc123@o123456.ingest.sentry.io/123456",
            "ALLOWED_HOSTS": '["test.com"]',
        }
    )

    assert validator.validate_settings()
    assert not validator.issues["errors"]
    assert not validator.issues["security_concerns"]


def test_full_validation_failure(validator, test_env):
    """Test full validation with invalid configuration."""
    os.environ.update(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "short",
            "DEBUG": "true",
            "SENTRY_ENABLED": "true",
            "ALLOWED_HOSTS": '["*"]',
        }
    )

    assert not validator.validate_settings()
    assert validator.issues["errors"] or validator.issues["security_concerns"]
