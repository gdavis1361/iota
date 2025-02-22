from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from scripts.monitoring import config
from scripts.monitoring.generate_performance_report import PerformanceReporter


@pytest.fixture
def mock_prometheus():
    with patch("scripts.monitoring.generate_performance_report.PrometheusConnect") as mock:
        yield mock


@pytest.fixture
def mock_config():
    with (
        patch(
            "scripts.monitoring.config.ALERT_THRESHOLDS",
            {
                "latency": {"warning": 1.0, "critical": 2.0},
                "memory": {"warning": 750, "critical": 1000},
                "rejection_rate": {"warning": 10.0, "critical": 20.0},
                "redis_errors": {"warning": 0, "critical": 1},
            },
        ),
        patch(
            "scripts.monitoring.config.METRIC_COLLECTION",
            {
                "interval_minutes": 5,
                "query_timeout_seconds": 30,
                "retention_days": 30,
                "resolution_minutes": {"recent": 1, "historical": 5},
            },
        ),
    ):
        yield


@pytest.fixture
def reporter(mock_prometheus, mock_config):
    return PerformanceReporter("http://localhost:9090")


def test_get_rate_limiter_metrics(reporter, mock_prometheus):
    # Mock response data
    mock_data = [
        {
            "values": [
                [1234567890, "10.5"],  # timestamp, value pairs
                [1234567891, "11.5"],
                [1234567892, "12.5"],
            ]
        }
    ]

    mock_instance = mock_prometheus.return_value
    mock_instance.custom_query_range.return_value = mock_data

    metrics = reporter.get_rate_limiter_metrics(60)

    assert metrics["requests_per_second"] == {"min": 10.5, "max": 12.5, "avg": 11.5}
    assert mock_instance.custom_query_range.call_count == 5  # One call for each metric


def test_query_metric_formatting(reporter, mock_prometheus):
    start_time = datetime.now() - timedelta(minutes=60)
    end_time = datetime.now()

    mock_instance = mock_prometheus.return_value
    mock_instance.custom_query_range.return_value = [
        {"values": [[1234567890, "10.5"], [1234567891, "11.5"]]}
    ]

    result = reporter._query_metric("test_query", start_time, end_time)

    # Verify the function was called with datetime objects and correct step
    mock_instance.custom_query_range.assert_called_once()
    call_args = mock_instance.custom_query_range.call_args[1]
    assert isinstance(call_args["start_time"], datetime)
    assert isinstance(call_args["end_time"], datetime)
    assert call_args["step"] == "5m"

    # Verify the result format
    assert result == {"min": 10.5, "max": 11.5, "avg": 11.0}


def test_threshold_violations(reporter, mock_prometheus):
    mock_instance = mock_prometheus.return_value

    # Mock data that should trigger violations
    mock_instance.custom_query_range.return_value = [
        {"values": [[1234567890, "3.0"], [1234567891, "3.0"]]}  # High latency (3ms)
    ]

    report = reporter.generate_report(60)

    # Check that violations are correctly identified
    assert "High Latency: Critical" in report


def test_memory_formatting(reporter, mock_prometheus):
    mock_instance = mock_prometheus.return_value

    # Mock memory data (in bytes)
    mock_instance.custom_query_range.return_value = [
        {
            "values": [
                [1234567890, str(500 * 1024 * 1024)],  # 500MB
                [1234567891, str(600 * 1024 * 1024)],  # 600MB
            ]
        }
    ]

    report = reporter.generate_report(60)

    # Verify memory is correctly converted to MB in the report
    assert "500.00MB" in report
    assert "600.00MB" in report
    assert "Memory Usage: No" in report


def test_error_handling(reporter, mock_prometheus):
    mock_instance = mock_prometheus.return_value
    mock_instance.custom_query_range.side_effect = Exception("Test error")

    # Should return zero values when query fails
    result = reporter._query_metric("test_query", datetime.now(), datetime.now())
    assert result == {"min": 0, "max": 0, "avg": 0}


def test_check_threshold_violation(reporter):
    # Test critical threshold
    assert reporter._check_threshold_violation("latency", 2.5) == "Critical"
    # Test warning threshold
    assert reporter._check_threshold_violation("latency", 1.5) == "Warning"
    # Test no violation
    assert reporter._check_threshold_violation("latency", 0.5) == "No"
    # Test unknown metric
    assert reporter._check_threshold_violation("unknown", 100) == "No"


def test_empty_metrics(reporter, mock_prometheus):
    mock_instance = mock_prometheus.return_value
    mock_instance.custom_query_range.return_value = []

    metrics = reporter.get_rate_limiter_metrics(60)

    for metric in metrics.values():
        assert metric["min"] == 0
        assert metric["max"] == 0
        assert metric["avg"] == 0


def test_generate_report(reporter, mock_prometheus):
    report = reporter.generate_report(60)

    assert "Performance Report" in report
    assert "Rate Limiter Performance" in report
    assert "System Health" in report
    assert "Threshold Violations" in report


@pytest.mark.parametrize("error_type", [ConnectionError, TimeoutError, Exception])
def test_error_handling_get_rate_limiter_metrics(reporter, mock_prometheus, error_type):
    mock_instance = mock_prometheus.return_value
    mock_instance.custom_query_range.side_effect = error_type("Test error")

    metrics = reporter.get_rate_limiter_metrics(60)

    for metric in metrics.values():
        assert metric["min"] == 0
        assert metric["max"] == 0
        assert metric["avg"] == 0
