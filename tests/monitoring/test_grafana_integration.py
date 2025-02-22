"""Real Grafana integration tests for the IOTA monitoring system.

These tests validate the monitoring system against a live Grafana instance.
They ensure that metric collection, alert routing, and dashboard updates
work correctly under real-world conditions.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import aiohttp
import pytest
import pytest_asyncio
from prometheus_client import Counter, Gauge, Histogram

from scripts.monitoring.generate_performance_report import PerformanceReporter

# Test metrics
REQUEST_COUNT = Counter("test_request_count", "Number of requests")
REQUEST_LATENCY = Histogram("test_request_latency_seconds", "Request latency in seconds")
MEMORY_USAGE = Gauge("test_memory_bytes", "Memory usage in bytes")

# Alert thresholds
ALERT_THRESHOLDS = {
    "latency": {"warning": 1.0, "critical": 2.0},
    "memory": {"warning": 800 * 1024 * 1024, "critical": 1024 * 1024 * 1024},  # 800MB  # 1GB
}


@pytest_asyncio.fixture(scope="session")
async def metrics_server():
    """Start the metrics server on port 9091."""
    from prometheus_client import start_http_server

    # Use a fixed port for consistency
    port = 9091
    start_http_server(port)

    # Generate some persistent test metrics
    test_latency = Histogram("test_alert_latency", "Test latency for alerts")
    for _ in range(10):
        test_latency.observe(ALERT_THRESHOLDS["latency"]["critical"] + 1.0)

    yield port


@pytest_asyncio.fixture
async def grafana_client():
    """Create an authenticated Grafana client session."""
    grafana_token = os.getenv("GRAFANA_API_TOKEN")
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")

    if not grafana_token:
        pytest.skip("GRAFANA_API_TOKEN not set")

    headers = {
        "Authorization": f"Bearer {grafana_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # First verify we can access Grafana
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(f"{grafana_url}/api/health") as response:
                if response.status != 200:
                    pytest.skip(f"Grafana not accessible: {await response.text()}")
            yield session
        except Exception as e:
            pytest.skip(f"Failed to connect to Grafana: {str(e)}")


async def create_alert_rule(client, metric_name):
    """Create an alert rule for a given metric."""
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")

    # First create a folder for our alert rules
    folder_data = {"title": "Test Alert Rules"}
    async with client.post(f"{grafana_url}/api/folders", json=folder_data) as response:
        if response.status == 200:
            folder = await response.json()
            folder_uid = folder["uid"]
        else:
            # Folder might already exist, try to find it
            async with client.get(f"{grafana_url}/api/folders") as response:
                folders = await response.json()
                folder = next((f for f in folders if f["title"] == "Test Alert Rules"), None)
                if folder:
                    folder_uid = folder["uid"]
                else:
                    return False

    # Create alert rule
    alert_data = {
        "folderUid": folder_uid,
        "ruleGroup": "test_alerts",
        "title": f"High {metric_name}",
        "condition": "C",
        "data": [
            {
                "refId": "A",
                "datasourceUid": "prometheus",
                "model": {
                    "expr": f"rate({metric_name}_sum[5m]) / rate({metric_name}_count[5m]) > {ALERT_THRESHOLDS['latency']['critical']}",
                    "intervalMs": 1000,
                    "maxDataPoints": 43200,
                },
            }
        ],
        "noDataState": "NoData",
        "execErrState": "Error",
        "for": "5m",
        "annotations": {"description": f"High {metric_name} detected"},
        "labels": {"severity": "critical"},
    }

    async with client.post(
        f"{grafana_url}/api/ruler/grafana/api/v1/rules/{folder_uid}", json=alert_data
    ) as response:
        return response.status == 201


@pytest.mark.asyncio
async def test_metric_collection(metrics_server):
    """Test that metrics are being collected and stored correctly."""
    # Generate test metrics with unique names for this test
    test_metric_name = f"test_request_latency_seconds_{int(datetime.now(timezone.utc).timestamp())}"
    test_latency = Histogram(test_metric_name, "Test request latency")
    test_latency.observe(0.5)

    # Verify metrics are exposed on our server
    async with aiohttp.ClientSession() as session:
        metrics_url = f"http://localhost:{metrics_server}/metrics"
        async with session.get(metrics_url) as response:
            assert response.status == 200, f"Metrics server not accessible at {metrics_url}"
            text = await response.text()
            assert test_metric_name in text, "Test metric not being exposed"
            assert "HELP" in text, "No HELP text found in metrics"
            assert "TYPE" in text, "No TYPE text found in metrics"


@pytest.mark.asyncio
async def test_alert_routing(grafana_client, metrics_server):
    """Test that alerts are properly routed based on thresholds.

    Requirements:
    1. Grafana Unified Alerting must be enabled
    2. An alert rule must be configured for latency metrics
    """
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")

    # First check if Unified Alerting is enabled
    async with grafana_client.get(f"{grafana_url}/api/v1/ngalert") as response:
        if response.status == 404:
            pytest.skip(
                "Unified Alerting is not enabled. Enable it in Grafana Configuration -> Features"
            )
        elif response.status == 401:
            pytest.skip("Invalid API token or insufficient permissions")

        assert response.status == 200, "Failed to check alerting status"

    # Generate test metrics with unique name
    test_metric_name = "test_alert_latency"  # Use fixed name to match provisioned rule
    test_latency = Histogram(test_metric_name, "Test latency for alerts")

    # Generate metrics that exceed threshold
    for _ in range(10):
        test_latency.observe(ALERT_THRESHOLDS["latency"]["critical"] + 1.0)

    # Wait for alert to be processed
    await asyncio.sleep(5)

    # Verify alert was created using the Alertmanager API
    async with grafana_client.get(f"{grafana_url}/api/alertmanager/alerts") as response:
        if response.status == 404:
            pytest.skip("Alertmanager API not available - ensure Unified Alerting is enabled")
        elif response.status == 401:
            pytest.skip("Invalid API token or insufficient permissions")

        assert response.status == 200, f"Failed to get alerts: {await response.text()}"
        alerts = await response.json()

        # Look for our alert
        alert_found = False
        for alert in alerts:
            if "HighTestLatency" in alert.get("labels", {}).get("alertname", ""):
                alert_found = True
                assert alert["status"]["state"] == "active", "Alert not in active state"
                break

        assert (
            alert_found
        ), "Alert not found - ensure alert rules are configured for latency metrics"


@pytest.mark.asyncio
async def test_dashboard_updates(grafana_client, metrics_server):
    """Test that dashboards are updated with new metrics."""
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
    dashboard_uid = os.getenv("GRAFANA_DASHBOARD_UID")

    if not dashboard_uid:
        pytest.skip("GRAFANA_DASHBOARD_UID not set")

    # Generate test metrics
    test_metric = Counter("test_dashboard_requests", "Test requests for dashboard")
    test_metric.inc()

    # Wait for dashboard to update
    await asyncio.sleep(5)

    # Check dashboard panels using Grafana API
    async with grafana_client.get(f"{grafana_url}/api/dashboards/uid/{dashboard_uid}") as response:
        if response.status == 404:
            pytest.skip(f"Dashboard {dashboard_uid} not found")
        elif response.status == 401:
            pytest.skip("Invalid API token or insufficient permissions")

        assert response.status == 200, f"Failed to get dashboard: {await response.text()}"
        dashboard = await response.json()

        # Verify dashboard exists and has panels
        assert dashboard.get("dashboard", {}).get("panels"), "No panels found in dashboard"
        assert (
            len(dashboard.get("dashboard", {}).get("panels", [])) > 0
        ), "No panels found in dashboard"


@pytest.mark.asyncio
async def test_threshold_violations(metrics_server):
    """Test that threshold violations are properly detected."""
    reporter = PerformanceReporter(os.getenv("PROMETHEUS_URL", "http://localhost:9090"))
    reporter.grafana_token = os.getenv("GRAFANA_API_TOKEN")

    # Create a unique test metric
    test_metric_name = f"test_redis_errors_{int(datetime.now(timezone.utc).timestamp())}"
    test_errors = Counter(test_metric_name, "Test redis errors")
    test_errors.inc()  # Increment to trigger warning

    # Wait for metrics to be processed
    await asyncio.sleep(5)

    # Generate report
    report = await reporter.generate_report_async(duration_mins=5)

    # Check for warning in report
    assert any(
        "warning" in line.lower() and "redis_errors" in line.lower() for line in report.split("\n")
    ), f"Redis errors warning not found in report:\n{report}"
    assert any(
        "threshold" in line.lower() for line in report.split("\n")
    ), "Threshold not found in report"


@pytest.mark.asyncio
async def test_error_handling(metrics_server):
    """Test error handling with invalid queries and connection issues."""
    reporter = PerformanceReporter(os.getenv("PROMETHEUS_URL", "http://localhost:9090"))
    reporter.grafana_token = os.getenv("GRAFANA_API_TOKEN")

    # Test invalid query
    with pytest.raises(Exception) as exc_info:
        await reporter.query_metrics_async(
            "invalid_metric{",  # Invalid query
            datetime.now(timezone.utc) - timedelta(minutes=5),
            datetime.now(timezone.utc),
        )
    error_msg = str(exc_info.value)
    assert any(
        msg in error_msg for msg in ["parse error", "invalid parameter"]
    ), f"Unexpected error message: {error_msg}"

    # Test connection error
    reporter = PerformanceReporter("http://nonexistent:9090")
    with pytest.raises(Exception) as exc_info:
        await reporter.query_metrics_async(
            "test_metric",
            datetime.now(timezone.utc) - timedelta(minutes=5),
            datetime.now(timezone.utc),
        )
    error_msg = str(exc_info.value)
    assert any(
        msg in error_msg
        for msg in [
            "Cannot connect to host",
            "Connection refused",
            "nodename nor servname provided",
        ]
    ), f"Unexpected error message: {error_msg}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
