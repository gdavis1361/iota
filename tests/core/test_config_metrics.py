"""Test configuration metrics collection."""

import os

import pytest

from server.core.config import Settings, get_settings
from server.core.config_schema import ConfigurationMetrics


@pytest.fixture
def clean_metrics():
    """Reset metrics between tests."""
    metrics = ConfigurationMetrics.get_instance()
    metrics.reset()
    yield metrics
    metrics.reset()


@pytest.fixture
def clean_env(monkeypatch):
    """Set up a clean test environment."""
    # Store original environment
    original_env = dict(os.environ)

    # Set up test environment
    test_env = {
        "ENVIRONMENT": "test",
        "SECRET_KEY": "test_secret_key_that_is_at_least_32_chars_long",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "console",
        "APP_NAME": "iota-test",
        "ALLOWED_HOSTS": '["localhost", "127.0.0.1"]',
        "SAMPLE_RATE": "0.1",
        "TRACE_RATE": "0.01",
        "SENTRY_ENABLED": "false",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    yield

    # Restore original environment
    for key in test_env:
        if key in original_env:
            monkeypatch.setenv(key, original_env[key])
        else:
            monkeypatch.delenv(key)


def test_metrics_singleton(clean_metrics):
    """Test that metrics follow singleton pattern."""
    metrics1 = ConfigurationMetrics.get_instance()
    metrics2 = ConfigurationMetrics.get_instance()
    assert metrics1 is metrics2


def test_metrics_reset(clean_metrics):
    """Test metrics reset functionality."""
    metrics = clean_metrics

    # Record some metrics
    metrics.record_validation(100.0)
    metrics.record_error("test", "error")
    metrics.record_warning()

    assert metrics.validation_time_ms == 100.0
    assert metrics.error_count == 1
    assert metrics.warning_count == 1

    # Reset metrics
    metrics.reset()

    assert metrics.validation_time_ms == 0.0
    assert metrics.error_count == 0
    assert metrics.warning_count == 0
    assert not metrics.validation_errors


def test_validation_timing_metrics(clean_metrics, clean_env):
    """Test that validation timing metrics are recorded."""
    metrics = clean_metrics

    # Initialize settings to trigger validation
    settings = get_settings()

    assert metrics.validation_time_ms > 0
    assert metrics.validation_count > 0
    assert metrics.last_validation_timestamp is not None
    assert metrics.average_validation_time_ms > 0


def test_error_recording(clean_metrics, clean_env, monkeypatch):
    """Test error recording in metrics."""
    metrics = clean_metrics

    # Trigger validation error with invalid environment
    monkeypatch.setenv("ENVIRONMENT", "invalid")

    with pytest.raises(ValueError):
        settings = Settings()

    assert metrics.error_count > 0
    assert "ENVIRONMENT" in metrics.validation_errors
    assert "invalid environment" in metrics.validation_errors["ENVIRONMENT"].lower()


def test_warning_recording(clean_metrics, clean_env, monkeypatch):
    """Test warning recording in metrics."""
    metrics = clean_metrics

    # Trigger warning by setting DEBUG=true in production
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings()

    assert metrics.warning_count > 0
    assert not settings.DEBUG  # Should be forced to False in production


def test_performance_metrics(clean_metrics, clean_env):
    """Test performance metrics recording."""
    metrics = clean_metrics

    # Multiple validation runs to test averaging
    for _ in range(3):
        settings = Settings()

    assert metrics.validation_count == 3
    assert metrics.peak_validation_time_ms > 0
    assert metrics.average_validation_time_ms > 0
    assert metrics.last_validation_timestamp is not None


def test_metrics_persistence(clean_metrics, clean_env):
    """Test that metrics persist between settings instances."""
    metrics = clean_metrics

    # First settings instance
    settings1 = Settings()
    initial_count = metrics.validation_count

    # Second settings instance
    settings2 = Settings()

    assert metrics.validation_count == initial_count + 1
    assert metrics.validation_time_ms > 0
