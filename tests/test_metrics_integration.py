"""Integration tests for the metrics exporter and Prometheus endpoint."""

import time

import pytest
import requests
from prometheus_client.parser import text_string_to_metric_families

from scripts.metrics_exporter import ConfigValidationMetrics


class TestMetricsIntegration:
    @pytest.fixture
    def metrics_url(self):
        """Prometheus metrics endpoint."""
        return "http://localhost:9090/metrics"

    @pytest.fixture
    def metrics_exporter(self):
        """Initialize metrics exporter instance."""
        return ConfigValidationMetrics()

    def test_metrics_endpoint_availability(self, metrics_url):
        """Test that metrics endpoint is accessible."""
        response = requests.get(metrics_url)
        assert response.status_code == 200
        assert "text/plain" in response.headers["Content-Type"]

    def test_required_metrics_present(self, metrics_url):
        """Verify all required metrics are exposed."""
        response = requests.get(metrics_url)
        metrics = {metric.name: metric for metric in text_string_to_metric_families(response.text)}

        required_metrics = [
            "config_validation_errors",
            "config_validation_warnings",
            "config_validation_security_issues",
            "config_validation_duration_seconds",
            "config_validation_last_timestamp",
        ]

        for metric_name in required_metrics:
            assert metric_name in metrics, f"Missing required metric: {metric_name}"

    def test_metric_type_validation(self, metrics_url):
        """Verify metric types are correct."""
        response = requests.get(metrics_url)
        metrics = {metric.name: metric for metric in text_string_to_metric_families(response.text)}

        # Counter metrics
        counters = [
            "config_validation_errors",
            "config_validation_warnings",
            "config_validation_security_issues",
        ]
        for metric_name in counters:
            assert metrics[metric_name].type == "counter"

        # Gauge metrics
        gauges = ["config_validation_duration_seconds", "config_validation_last_timestamp"]
        for metric_name in gauges:
            assert metrics[metric_name].type == "gauge"

    def test_metric_updates(self, metrics_exporter):
        """Test that metrics are properly updated."""
        # Record initial values
        initial_errors = metrics_exporter.validation_errors._value.get()
        initial_warnings = metrics_exporter.validation_warnings._value.get()

        # Simulate validation events
        metrics_exporter.record_validation_error()
        metrics_exporter.record_validation_warning()
        metrics_exporter.record_security_issue()

        # Verify counters increased
        assert metrics_exporter.validation_errors._value.get() == initial_errors + 1
        assert metrics_exporter.validation_warnings._value.get() == initial_warnings + 1
        assert metrics_exporter.security_issues._value.get() > 0

    def test_duration_tracking(self, metrics_exporter):
        """Test validation duration tracking."""
        with metrics_exporter.track_validation_duration():
            time.sleep(0.1)  # Simulate validation work

        duration = metrics_exporter.validation_duration._value.get()
        assert duration >= 0.1, "Duration tracking failed"

    def test_timestamp_updates(self, metrics_exporter):
        """Test last validation timestamp updates."""
        initial_timestamp = metrics_exporter.last_validation_timestamp._value.get()

        # Simulate validation
        with metrics_exporter.track_validation_duration():
            pass

        new_timestamp = metrics_exporter.last_validation_timestamp._value.get()
        assert new_timestamp > initial_timestamp, "Timestamp not updated"

    def test_metric_labels(self, metrics_url):
        """Test metric labels are present and correct."""
        response = requests.get(metrics_url)
        metrics = list(text_string_to_metric_families(response.text))

        for metric in metrics:
            if metric.name.startswith("config_validation_"):
                # Verify common labels
                for sample in metric.samples:
                    assert "environment" in sample.labels
                    assert "version" in sample.labels

    def test_metric_help_text(self, metrics_url):
        """Verify metrics have helpful descriptions."""
        response = requests.get(metrics_url)
        metrics = list(text_string_to_metric_families(response.text))

        for metric in metrics:
            if metric.name.startswith("config_validation_"):
                assert metric.documentation, f"Missing help text for {metric.name}"
                assert len(metric.documentation) > 10, f"Help text too short for {metric.name}"
