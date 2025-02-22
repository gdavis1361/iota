"""Script to generate test metrics for Grafana alerting tests."""

import time

from prometheus_client import Histogram, start_http_server

# Alert thresholds
ALERT_THRESHOLDS = {"latency": {"warning": 1.0, "critical": 2.0}}


def main():
    """Generate test metrics."""
    # Start up the server to expose the metrics.
    port = 9091
    start_http_server(port)
    print(f"Serving metrics on port {port}")

    # Create metrics
    test_latency = Histogram("test_alert_latency", "Test latency for alerts")

    while True:
        # Generate high latency metrics to trigger alert
        test_latency.observe(ALERT_THRESHOLDS["latency"]["critical"] + 1.0)
        time.sleep(1)


if __name__ == "__main__":
    main()
