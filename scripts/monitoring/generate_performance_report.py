#!/usr/bin/env python3

"""Generate performance report from test results."""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

import aiohttp
from prometheus_api_client import PrometheusConnect

from . import config

logger = logging.getLogger(__name__)


class PerformanceReporter:
    """Generate performance reports from test results."""

    def __init__(self, prometheus_url: str):
        """Initialize reporter with Prometheus URL."""
        self.prometheus_url = prometheus_url
        self.prometheus = PrometheusConnect(url=prometheus_url)
        self.thresholds = config.ALERT_THRESHOLDS
        self.collection_config = config.METRIC_COLLECTION
        self.grafana_token = os.getenv("GRAFANA_API_TOKEN")

    async def query_metrics_async(
        self, query: str, start_time: datetime, end_time: datetime, step: str = "1m"
    ) -> list:
        """Query metrics asynchronously from Prometheus."""
        params = {
            "query": query,
            "start": int(start_time.timestamp()),
            "end": int(end_time.timestamp()),
            "step": step,
        }

        timeout = aiohttp.ClientTimeout(
            total=self.collection_config.get("query_timeout_seconds", 30)
        )

        headers = {"Authorization": f"Bearer {self.grafana_token}"}

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{self.prometheus_url}/api/v1/query_range", params=params, headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    if "Invalid query" in error_text:
                        raise Exception(f"Invalid query: {query}")
                    raise Exception(f"Query failed: {error_text}")

                data = await response.json()
                if data["status"] != "success":
                    raise Exception(f"Query failed: {data.get('error', 'Unknown error')}")

                return data["data"]["result"]

    async def _query_metric_async(
        self, query: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, float]:
        """Query a metric asynchronously and return min/max/avg values."""
        try:
            result = await self.query_metrics_async(
                query,
                start_time,
                end_time,
                step=f"{self.collection_config['interval_minutes']}m",
            )

            if not result:
                return {"min": 0.0, "max": 0.0, "avg": 0.0}

            values = [float(v[1]) for v in result[0]["values"]]
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
            }
        except Exception as e:
            print(f"Error querying metric {query}: {e}", file=sys.stderr)
            return {"min": 0.0, "max": 0.0, "avg": 0.0, "error": str(e)}

    async def get_rate_limiter_metrics_async(
        self, duration_mins: int = 60
    ) -> Dict[str, Dict[str, float]]:
        """Get rate limiter metrics asynchronously for the specified duration."""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=duration_mins)

        metrics = {
            "requests_per_second": await self._query_metric_async(
                "sum(rate(rate_limit_requests_total[5m]))",
                start_time,
                end_time,
            ),
            "rejection_rate": await self._query_metric_async(
                'sum(rate(rate_limit_requests_total{limited="true"}[5m])) / sum(rate(rate_limit_requests_total[5m])) * 100',
                start_time,
                end_time,
            ),
            "average_latency": await self._query_metric_async(
                "rate(rate_limit_duration_sum[5m]) / rate(rate_limit_duration_count[5m])",
                start_time,
                end_time,
            ),
            "redis_errors": await self._query_metric_async(
                "sum(rate(redis_errors_total[5m]))",
                start_time,
                end_time,
            ),
            "memory_usage": await self._query_metric_async(
                'process_resident_memory_bytes{job="iota"}',
                start_time,
                end_time,
            ),
        }

        return metrics

    async def generate_report_async(
        self, duration_mins: int = 60, thresholds: Optional[Dict[str, Dict[str, float]]] = None
    ) -> str:
        """Generate a performance report asynchronously."""
        if thresholds is None:
            thresholds = self.thresholds

        metrics = await self.get_rate_limiter_metrics_async(duration_mins)

        report = []
        report.append(f"Performance Report (Last {duration_mins} minutes)")
        report.append("=" * 50)

        # Check thresholds and format metrics
        for metric_name, values in metrics.items():
            if "error" in values:
                report.append(f"\n{metric_name}: Error - {values['error']}")
                continue

            report.append(f"\n{metric_name}:")
            report.append(f"  Min: {values['min']:.2f}")
            report.append(f"  Max: {values['max']:.2f}")
            report.append(f"  Avg: {values['avg']:.2f}")

            # Check thresholds
            if metric_name in thresholds:
                threshold = thresholds[metric_name]
                if values["max"] >= threshold["critical"]:
                    report.append(f"  CRITICAL: {metric_name} exceeds critical threshold")
                elif values["max"] >= threshold["warning"]:
                    report.append(f"  WARNING: {metric_name} exceeds warning threshold")

        return "\n".join(report)

    # Keep synchronous methods for backward compatibility
    def query_metrics(self, *args, **kwargs):
        """Synchronous wrapper for query_metrics_async."""
        import asyncio

        return asyncio.run(self.query_metrics_async(*args, **kwargs))

    def get_rate_limiter_metrics(self, *args, **kwargs):
        """Synchronous wrapper for get_rate_limiter_metrics_async."""
        import asyncio

        return asyncio.run(self.get_rate_limiter_metrics_async(*args, **kwargs))

    def generate_report(self, *args, **kwargs):
        """Synchronous wrapper for generate_report_async."""
        import asyncio

        return asyncio.run(self.generate_report_async(*args, **kwargs))


async def main_async():
    """Async main function."""
    parser = argparse.ArgumentParser(description="Generate performance report")
    parser.add_argument(
        "--prometheus-url",
        default="http://localhost:9090",
        help="Prometheus URL",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in minutes",
    )
    args = parser.parse_args()

    reporter = PerformanceReporter(args.prometheus_url)
    report = await reporter.generate_report_async(args.duration)
    print(report)


def main():
    """Synchronous entry point."""
    import asyncio

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
