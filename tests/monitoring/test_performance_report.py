import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from prometheus_api_client import PrometheusConnect

from scripts.monitoring.generate_performance_report import PerformanceReporter


@pytest.fixture
def mock_prometheus_data():
    return [
        {
            "values": [
                [1614556800, "10.5"],
                [1614556860, "11.2"],
                [1614556920, "9.8"]
            ]
        }
    ]

@pytest.fixture
def mock_prom():
    with patch('prometheus_api_client.PrometheusConnect') as mock:
        prom = mock.return_value
        prom.custom_query_range.return_value = [{
            "values": [
                [1614556800, "10.5"],
                [1614556860, "11.2"],
                [1614556920, "9.8"]
            ]
        }]
        yield prom

def test_get_rate_limiter_metrics(mock_prom):
    reporter = PerformanceReporter("http://localhost:9090")
    metrics = reporter.get_rate_limiter_metrics(duration_mins=5)
    
    assert "requests_per_second" in metrics
    assert "rejection_rate" in metrics
    assert "average_latency" in metrics
    assert "redis_errors" in metrics
    assert "memory_usage" in metrics
    
    # Verify metric calculations
    for metric in metrics.values():
        assert "min" in metric
        assert "max" in metric
        assert "avg" in metric
        assert metric["min"] == 9.8
        assert metric["max"] == 11.2
        assert abs(metric["avg"] - 10.5) < 0.1

def test_empty_metrics(mock_prom):
    mock_prom.custom_query_range.return_value = []
    
    reporter = PerformanceReporter("http://localhost:9090")
    metrics = reporter.get_rate_limiter_metrics(duration_mins=5)
    
    for metric in metrics.values():
        assert metric["min"] == 0
        assert metric["max"] == 0
        assert metric["avg"] == 0

def test_generate_report(mock_prom):
    reporter = PerformanceReporter("http://localhost:9090")
    report = reporter.generate_report(duration_mins=5)
    
    assert "Performance Report" in report
    assert "Rate Limiter Performance" in report
    assert "System Health" in report
    assert "Threshold Violations" in report

@pytest.mark.parametrize("error_type", [
    ConnectionError,
    TimeoutError,
    Exception
])
def test_error_handling(mock_prom, error_type):
    mock_prom.custom_query_range.side_effect = error_type("Test error")
    
    reporter = PerformanceReporter("http://localhost:9090")
    metrics = reporter.get_rate_limiter_metrics(duration_mins=5)
    
    for metric in metrics.values():
        assert metric["min"] == 0
        assert metric["max"] == 0
        assert metric["avg"] == 0

def test_query_metric_formatting(mock_prom):
    reporter = PerformanceReporter("http://localhost:9090")
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    
    reporter._query_metric(
        'test_query',
        start_time,
        end_time
    )
    
    mock_prom.custom_query_range.assert_called_once()
    args = mock_prom.custom_query_range.call_args[1]
    
    assert "test_query" in args["query"]
    assert args["start_time"].endswith("Z")
    assert args["end_time"].endswith("Z")
    assert args["step"] == "5m"

def test_threshold_violations(mock_prom):
    # Mock high latency
    mock_prom.custom_query_range.return_value = [{
        "values": [
            [1614556800, "0.002"],  # 2ms
            [1614556860, "0.001"],  # 1ms
            [1614556920, "0.003"]   # 3ms
        ]
    }]
    
    reporter = PerformanceReporter("http://localhost:9090")
    report = reporter.generate_report(duration_mins=5)
    
    assert "High Latency: Yes" in report

def test_memory_formatting(mock_prom):
    # Mock memory values in bytes
    mock_prom.custom_query_range.return_value = [{
        "values": [
            [1614556800, "104857600"],  # 100MB
            [1614556860, "115343360"],  # 110MB
            [1614556920, "94371840"]    # 90MB
        ]
    }]
    
    reporter = PerformanceReporter("http://localhost:9090")
    report = reporter.generate_report(duration_mins=5)
    
    assert "MB" in report
    assert "100.00MB" in report or "100MB" in report
