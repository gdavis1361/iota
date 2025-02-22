"""Test suite for validation metrics exporter."""

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry

from scripts.metrics_exporter import ValidationMetricsExporter


class TestMetricsExporter:
    """Test cases for validation metrics exporter."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures."""
        # Create a test metrics file
        self.temp_dir = tempfile.mkdtemp()
        self.metrics_file = Path(self.temp_dir) / "validation_metrics.json"
        self.test_metrics = {
            "error_count": 2,
            "warning_count": 3,
            "security_count": 1,
            "validation_time_ms": 123.45,
            "errors": ["Error 1", "Error 2"],
            "warnings": ["Warning 1", "Warning 2", "Warning 3"],
            "security_concerns": ["Security Issue 1"],
            "last_validation": datetime.now(timezone.utc).isoformat(),
        }

        with open(self.metrics_file, "w") as f:
            json.dump(self.test_metrics, f)

        # Create metrics exporter with fresh registry
        self.registry = CollectorRegistry()
        self.exporter = ValidationMetricsExporter(port=9091, registry=self.registry)

        yield

        # Cleanup
        if self.metrics_file.exists():
            self.metrics_file.unlink()
        os.rmdir(self.temp_dir)

    def test_metrics_initialization(self):
        """Test metrics are properly initialized."""
        assert self.exporter.error_count._value.get() == 0
        assert self.exporter.warning_count._value.get() == 0
        assert self.exporter.security_count._value.get() == 0
        assert self.exporter.validation_time._value.get() == 0
        assert self.exporter.last_validation._value.get() == 0

    def test_update_metrics(self):
        """Test metrics update from file."""
        self.exporter.update_metrics(self.metrics_file)

        # Check counter values
        assert self.exporter.error_count._value.get() == self.test_metrics["error_count"]
        assert self.exporter.warning_count._value.get() == self.test_metrics["warning_count"]
        assert self.exporter.security_count._value.get() == self.test_metrics["security_count"]

        # Check gauge values
        assert (
            self.exporter.validation_time._value.get()
            == self.test_metrics["validation_time_ms"] / 1000.0
        )

    def test_missing_metrics_file(self):
        """Test handling of missing metrics file."""
        missing_file = Path(self.temp_dir) / "missing.json"
        self.exporter.update_metrics(missing_file)

        # All metrics should remain at 0
        assert self.exporter.error_count._value.get() == 0

    def test_invalid_metrics_file(self):
        """Test handling of invalid metrics file."""
        # Create invalid JSON
        with open(self.metrics_file, "w") as f:
            f.write("invalid json")

        self.exporter.update_metrics(self.metrics_file)

        # All metrics should remain at 0
        assert self.exporter.error_count._value.get() == 0

    def test_server_start(self):
        """Test metrics server startup."""
        with patch("scripts.metrics_exporter.start_http_server") as mock_server:
            self.exporter.start()
            mock_server.assert_called_once_with(self.exporter.port, registry=self.registry)

    def test_multiple_updates(self):
        """Test multiple metric updates."""
        # First update
        self.exporter.update_metrics(self.metrics_file)
        first_errors = self.exporter.error_count._value.get()

        # Update metrics file
        self.test_metrics["error_count"] = 5
        with open(self.metrics_file, "w") as f:
            json.dump(self.test_metrics, f)

        # Second update
        self.exporter.update_metrics(self.metrics_file)
        second_errors = self.exporter.error_count._value.get()

        assert second_errors - first_errors == 3

    def test_timestamp_conversion(self):
        """Test timestamp conversion for last validation metric."""
        self.exporter.update_metrics(self.metrics_file)

        last_validation = self.exporter.last_validation._value.get()
        assert last_validation > 0
        assert isinstance(last_validation, float)

    def test_metric_labels(self):
        """Test metric label consistency."""
        # Update metrics to ensure all metrics are registered
        self.exporter.update_metrics(self.metrics_file)

        # Get all metric names with their full names
        metric_names = {
            "config_validation_errors",
            "config_validation_warnings",
            "config_validation_security_issues",
            "config_validation_duration_seconds",
            "config_validation_last_timestamp",
        }

        # Check each metric exists
        for name in metric_names:
            assert name in [
                metric._name for metric in self.registry._names_to_collectors.values()
            ], f"Missing metric: {name}"
