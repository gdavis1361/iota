#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from prometheus_api_client import PrometheusConnect


class PerformanceReporter:
    def __init__(self, prometheus_url: str):
        self.prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)

    def get_rate_limiter_metrics(self, duration_mins: int = 60) -> Dict:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=duration_mins)

        metrics = {
            "requests_per_second": self._query_metric(
                "sum(rate(rate_limit_requests_total[5m]))", start_time, end_time
            ),
            "rejection_rate": self._query_metric(
                'sum(rate(rate_limit_requests_total{limited="true"}[5m])) / sum(rate(rate_limit_requests_total[5m])) * 100',
                start_time,
                end_time,
            ),
            "average_latency": self._query_metric(
                "rate(rate_limit_duration_sum[5m]) / rate(rate_limit_duration_count[5m])",
                start_time,
                end_time,
            ),
            "redis_errors": self._query_metric(
                "sum(rate(redis_errors_total[5m]))", start_time, end_time
            ),
            "memory_usage": self._query_metric(
                'process_resident_memory_bytes{job="iota"}', start_time, end_time
            ),
        }

        return metrics

    def _query_metric(self, query: str, start_time: datetime, end_time: datetime) -> Dict:
        result = self.prom.custom_query_range(
            query,
            start_time=start_time.isoformat("T") + "Z",
            end_time=end_time.isoformat("T") + "Z",
            step="5m",
        )

        if not result:
            return {"min": 0, "max": 0, "avg": 0}

        values = [float(v[1]) for v in result[0]["values"]]
        return {"min": min(values), "max": max(values), "avg": sum(values) / len(values)}

    def generate_report(self, duration_mins: int = 60) -> str:
        metrics = self.get_rate_limiter_metrics(duration_mins)

        report = [
            f"Performance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: Last {duration_mins} minutes",
            "",
            "Rate Limiter Performance:",
            f"- Requests/sec: {metrics['requests_per_second']['avg']:.2f} (min: {metrics['requests_per_second']['min']:.2f}, max: {metrics['requests_per_second']['max']:.2f})",
            f"- Rejection Rate: {metrics['rejection_rate']['avg']:.2f}% (min: {metrics['rejection_rate']['min']:.2f}%, max: {metrics['rejection_rate']['max']:.2f}%)",
            f"- Average Latency: {metrics['average_latency']['avg']*1000:.2f}ms (min: {metrics['average_latency']['min']*1000:.2f}ms, max: {metrics['average_latency']['max']*1000:.2f}ms)",
            "",
            "System Health:",
            f"- Redis Errors/min: {metrics['redis_errors']['avg']*60:.2f} (min: {metrics['redis_errors']['min']*60:.2f}, max: {metrics['redis_errors']['max']*60:.2f})",
            f"- Memory Usage: {metrics['memory_usage']['avg']/1024/1024:.2f}MB (min: {metrics['memory_usage']['min']/1024/1024:.2f}MB, max: {metrics['memory_usage']['max']/1024/1024:.2f}MB)",
            "",
            "Threshold Violations:",
            f"- High Latency: {'Yes' if metrics['average_latency']['max'] > 0.001 else 'No'}",
            f"- High Rejection Rate: {'Yes' if metrics['rejection_rate']['max'] > 20 else 'No'}",
            f"- Redis Errors: {'Yes' if metrics['redis_errors']['max'] > 0 else 'No'}",
            f"- Memory Usage: {'Yes' if metrics['memory_usage']['max'] > 1e9 else 'No'}",
        ]

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Generate performance report from Prometheus metrics"
    )
    parser.add_argument(
        "--prometheus-url", default="http://localhost:9090", help="Prometheus server URL"
    )
    parser.add_argument("--duration", type=int, default=60, help="Report duration in minutes")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    try:
        reporter = PerformanceReporter(args.prometheus_url)
        report = reporter.generate_report(args.duration)

        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
        else:
            print(report)

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
