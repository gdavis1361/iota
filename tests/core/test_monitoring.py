"""Tests for the performance monitoring module."""

import os
import time
from unittest import mock

import pytest

from server.core.monitoring import PerformanceMonitor


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    original_env = os.environ.copy()
    os.environ["ENV_FILE"] = "tests/core/test_settings.env"
    os.environ["ENVIRONMENT"] = "test"
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def monitor():
    """Get a fresh instance of PerformanceMonitor for each test."""
    # Reset the singleton
    PerformanceMonitor._instance = None
    monitor = PerformanceMonitor.get_instance()

    # Mock time.time() for consistent testing
    with mock.patch("time.time") as mock_time:
        mock_time.return_value = 1000.0  # Start at a known time
        yield monitor


def test_singleton_pattern():
    """Test that PerformanceMonitor is a singleton."""
    monitor1 = PerformanceMonitor.get_instance()
    monitor2 = PerformanceMonitor.get_instance()
    assert monitor1 is monitor2


def test_initial_rates(monitor):
    """Test initial sampling rates."""
    rates = monitor.get_current_sample_rates()
    assert rates["traces"] == 1.0
    assert rates["profiles"] == 1.0


def test_record_request_normal(monitor):
    """Test recording a normal request."""
    monitor.record_request(500)  # 500ms request
    assert monitor.request_count == 1
    assert monitor.error_count == 0
    assert monitor.slow_request_count == 0


def test_record_request_slow(monitor):
    """Test recording a slow request."""
    monitor.record_request(2000)  # 2000ms request
    assert monitor.request_count == 1
    assert monitor.error_count == 0
    assert monitor.slow_request_count == 1


def test_record_request_error(monitor):
    """Test recording a request with error."""
    monitor.record_request(500, had_error=True)
    assert monitor.request_count == 1
    assert monitor.error_count == 1
    assert monitor.slow_request_count == 0


def test_counter_reset(monitor):
    """Test counter reset after sampling window."""
    with mock.patch("time.time") as mock_time:
        # Initial request at t=1000
        mock_time.return_value = 1000.0
        monitor.record_request(500)
        assert monitor.request_count == 1

        # Second request after window at t=1061 (window = 60s)
        mock_time.return_value = 1061.0
        monitor.record_request(500)
        assert monitor.request_count == 1  # Should have reset to 0 and then incremented


def test_rate_increase_on_errors(monitor):
    """Test sampling rate increases when error threshold exceeded."""
    with mock.patch("time.time") as mock_time:
        # Generate enough errors to exceed threshold
        mock_time.return_value = 1000.0
        for _ in range(20):
            monitor.record_request(500, had_error=True)

        # Force a rate recalculation by simulating window expiry
        mock_time.return_value = 1061.0
        monitor.record_request(500)

        rates = monitor.get_current_sample_rates()
        assert rates["traces"] == 1.0  # Should be capped at 1.0
        assert rates["profiles"] == 1.0


def test_rate_decrease_on_success(monitor):
    """Test sampling rate decreases when error rate is low."""
    with mock.patch("time.time") as mock_time:
        # Generate many successful requests
        mock_time.return_value = 1000.0
        for _ in range(1000):
            monitor.record_request(500)

        # Force a rate recalculation
        mock_time.return_value = 1061.0
        monitor.record_request(500)

        rates = monitor.get_current_sample_rates()
        assert rates["traces"] == 0.5  # Should be halved
        assert rates["profiles"] == 0.5


def test_min_max_rates(monitor):
    """Test that sampling rates stay within bounds."""
    with mock.patch("time.time") as mock_time:
        # Test maximum (1.0)
        mock_time.return_value = 1000.0
        for _ in range(20):
            monitor.record_request(500, had_error=True)
        mock_time.return_value = 1061.0
        monitor.record_request(500)
        rates = monitor.get_current_sample_rates()
        assert rates["traces"] <= 1.0
        assert rates["profiles"] <= 1.0

        # Reset monitor
        PerformanceMonitor._instance = None
        monitor = PerformanceMonitor.get_instance()

        # Test minimum (0.01)
        mock_time.return_value = 1000.0
        for _ in range(1000):
            monitor.record_request(500)
        mock_time.return_value = 1061.0
        monitor.record_request(500)
        rates = monitor.get_current_sample_rates()
        assert rates["traces"] >= 0.01
        assert rates["profiles"] >= 0.01
