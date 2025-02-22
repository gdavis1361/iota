"""Tests for configuration monitoring system."""

import os
import time
from unittest.mock import patch

import pytest

from server.core.config import Settings
from server.core.config_schema import ConfigurationMetrics, ConfigVersion
from server.core.monitoring import ConfigurationMonitor, PerformanceMonitor


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment."""
    # Save original environment
    original_env = dict(os.environ)

    # Set test environment variables
    os.environ.update(
        {
            "SECRET_KEY": "x" * 32,
            "ENVIRONMENT": "test",
            "SENTRY_ENABLED": "false",
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "console",
            "SAMPLING_WINDOW_SECONDS": "60",
            "SLOW_REQUEST_THRESHOLD_MS": "1000",
            "ERROR_RATE_THRESHOLD": "0.1",
            "SLOW_RATE_THRESHOLD": "0.1",
        }
    )

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

    # Reset monitors
    ConfigurationMonitor._instance = None
    PerformanceMonitor._instance = None


def test_config_monitor_singleton():
    """Test configuration monitor singleton pattern."""
    monitor1 = ConfigurationMonitor.get_instance()
    monitor2 = ConfigurationMonitor.get_instance()
    assert monitor1 is monitor2


def test_config_monitor_metrics():
    """Test configuration monitor metrics tracking."""
    monitor = ConfigurationMonitor.get_instance()

    # Reset metrics
    monitor.total_validations = 0
    monitor.total_errors = 0
    monitor.total_warnings = 0
    monitor.avg_validation_time = 0.0

    # Create settings with some validation errors
    with pytest.raises(ValueError):
        Settings(
            SECRET_KEY="short",  # Too short
            ENVIRONMENT="invalid",  # Invalid environment
            SENTRY_ENABLED=True,  # Missing DSN
        )

    # Check metrics
    metrics = monitor.get_metrics()
    assert metrics["total_validations"] > 0
    assert metrics["total_errors"] > 0
    assert metrics["config_version"] == ConfigVersion.V2_0.value
    assert metrics["schema_version"] == ConfigVersion.V2_0.value


def test_config_monitor_health():
    """Test configuration monitor health check."""
    monitor = ConfigurationMonitor.get_instance()

    # Create valid settings
    settings = Settings(SECRET_KEY="x" * 32, ENVIRONMENT="test")

    # Check health
    health = monitor.check_health()
    assert health["status"] == "healthy"
    assert isinstance(health["last_check"], float)
    assert isinstance(health["current_time"], float)
    assert isinstance(health["metrics"], dict)


def test_config_monitor_validation_time():
    """Test validation time tracking."""
    monitor = ConfigurationMonitor.get_instance()

    # Reset metrics
    monitor.avg_validation_time = 0.0
    monitor.total_validations = 0

    # Create settings with simulated validation time
    with patch("time.time") as mock_time:
        mock_time.side_effect = [0.0, 0.1]  # 100ms validation time
        settings = Settings(SECRET_KEY="x" * 32, ENVIRONMENT="test")

    # Check metrics
    metrics = monitor.get_metrics()
    assert metrics["avg_validation_time_ms"] > 0


def test_config_monitor_version_mismatch():
    """Test version mismatch detection."""
    monitor = ConfigurationMonitor.get_instance()
    monitor.settings = None  # Reset settings

    # Create settings with old version
    settings = Settings(SECRET_KEY="x" * 32, ENVIRONMENT="test", version=ConfigVersion.V1_0.value)
    monitor.settings = settings
    monitor.settings_version = ConfigVersion.V1_0.value

    # Check metrics
    metrics = monitor.get_metrics()
    assert metrics["config_version"] == ConfigVersion.V1_0.value
    assert metrics["schema_version"] == ConfigVersion.V2_0.value
    assert metrics["config_version"] != metrics["schema_version"]

    # Health should show warnings
    health = monitor.check_health()
    assert health["metrics"]["total_warnings"] > 0


def test_performance_monitor_singleton():
    """Test performance monitor singleton pattern."""
    monitor1 = PerformanceMonitor.get_instance()
    monitor2 = PerformanceMonitor.get_instance()
    assert monitor1 is monitor2


def test_performance_monitor_sampling():
    """Test performance monitor sampling rate adjustments."""
    monitor = PerformanceMonitor.get_instance()

    # Test environment should have full sampling
    assert monitor.current_traces_rate == 1.0
    assert monitor.current_profiles_rate == 1.0

    # Record some requests
    for _ in range(10):
        monitor.record_request(500.0)  # Normal requests

    # Record some slow requests
    for _ in range(5):
        monitor.record_request(2000.0)  # Slow requests

    # Record some errors
    for _ in range(3):
        monitor.record_request(100.0, had_error=True)

    # Force rate recalculation
    monitor.last_reset = 0  # Reset timestamp to force recalculation
    monitor.record_request(100.0)  # Trigger recalculation

    # Rates should have adjusted based on error/slow request rates
    assert monitor.current_traces_rate > 0.0
    assert monitor.current_profiles_rate > 0.0
