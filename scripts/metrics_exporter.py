#!/usr/bin/env python3
"""Export configuration validation metrics to Prometheus."""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)

# Default registry for metrics
DEFAULT_REGISTRY = CollectorRegistry()


class ValidationMetricsExporter:
    """Export validation metrics to Prometheus."""

    def __init__(
        self,
        port: int = 9090,
        registry: Optional[CollectorRegistry] = None,
        metrics_file: Optional[Path] = None,
    ):
        """Initialize metrics exporter.

        Args:
            port: Port to expose metrics on
            registry: Optional custom registry for metrics
            metrics_file: Path to metrics JSON file
        """
        self.port = port
        self.registry = registry or DEFAULT_REGISTRY
        self.metrics_file = metrics_file or Path("validation_metrics.json")

        # Define metrics with consistent naming
        self.error_count = Counter(
            "config_validation_errors_total",
            "Total number of configuration validation errors",
            registry=self.registry,
        )

        self.warning_count = Counter(
            "config_validation_warnings_total",
            "Total number of configuration validation warnings",
            registry=self.registry,
        )

        self.security_count = Counter(
            "config_validation_security_issues_total",
            "Total number of configuration security issues",
            registry=self.registry,
        )

        self.validation_time = Gauge(
            "config_validation_duration_seconds",
            "Time taken for configuration validation",
            registry=self.registry,
        )

        self.last_validation = Gauge(
            "config_validation_last_timestamp",
            "Timestamp of last validation run",
            registry=self.registry,
        )

    def start(self):
        """Start the metrics server."""
        start_http_server(self.port, registry=self.registry)

    def update_metrics(self):
        """Update metrics from validation metrics file."""
        try:
            with open(self.metrics_file) as f:
                metrics = json.load(f)

            # Reset counters before updating
            self.error_count._value.set(0)
            self.warning_count._value.set(0)
            self.security_count._value.set(0)

            # Update counters with absolute values
            self.error_count._value.set(metrics.get("error_count", 0))
            self.warning_count._value.set(metrics.get("warning_count", 0))
            self.security_count._value.set(metrics.get("security_count", 0))

            # Update gauges
            self.validation_time.set(metrics.get("validation_time_ms", 0) / 1000.0)

            # Convert ISO timestamp to Unix timestamp
            if "last_validation" in metrics:
                import dateutil.parser

                ts = dateutil.parser.parse(metrics["last_validation"])
                self.last_validation.set(ts.timestamp())

            logger.info("Updated metrics")
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")


def main():
    """Main entry point."""
    exporter = ValidationMetricsExporter()
    exporter.start()

    print(f"Starting metrics server on port {exporter.port}")
    print("Metrics available at http://localhost:9090/metrics")

    while True:
        if exporter.metrics_file.exists():
            exporter.update_metrics()
        time.sleep(15)  # Check every 15 seconds


if __name__ == "__main__":
    main()
