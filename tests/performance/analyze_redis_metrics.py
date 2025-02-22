#!/usr/bin/env python3
"""Analyze Redis metrics from performance tests."""
import argparse
import json
import re
import sys
from typing import Dict, List


def parse_redis_info(log_file: str) -> List[Dict]:
    """Parse Redis INFO command output from log file."""
    metrics = []
    current_metrics = {}

    with open(log_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                if current_metrics:
                    metrics.append(current_metrics)
                    current_metrics = {}
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                current_metrics[key.strip()] = value.strip()

    if current_metrics:
        metrics.append(current_metrics)

    return metrics


def convert_to_bytes(size_str: str) -> int:
    """Convert size string (e.g., '1GB') to bytes."""
    units = {"B": 1, "KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}

    match = re.match(r"(\d+)([KMGT]?B)", size_str.upper())
    if not match:
        return int(size_str)

    size, unit = match.groups()
    return int(size) * units[unit]


def analyze_metrics(metrics: List[Dict], config: Dict) -> Dict:
    """Analyze Redis metrics against thresholds."""
    analysis = {
        "summary": {
            "total_samples": len(metrics),
            "threshold_violations": 0,
            "max_memory_usage": 0,
            "max_clients": 0,
            "avg_hit_rate": 0,
        },
        "violations": [],
        "recommendations": [],
    }

    # Memory analysis
    max_memory_threshold = convert_to_bytes(
        config["redis_monitoring"]["thresholds"]["max_memory_usage"]
    )
    for sample in metrics:
        memory_used = int(sample.get("used_memory", 0))
        analysis["summary"]["max_memory_usage"] = max(
            analysis["summary"]["max_memory_usage"], memory_used
        )

        if memory_used > max_memory_threshold:
            analysis["violations"].append(
                {
                    "type": "memory",
                    "value": memory_used,
                    "threshold": max_memory_threshold,
                    "message": "Memory usage exceeded threshold",
                }
            )

    # Client connections
    max_clients_threshold = config["redis_monitoring"]["thresholds"]["max_clients"]
    for sample in metrics:
        clients = int(sample.get("connected_clients", 0))
        analysis["summary"]["max_clients"] = max(analysis["summary"]["max_clients"], clients)

        if clients > max_clients_threshold:
            analysis["violations"].append(
                {
                    "type": "clients",
                    "value": clients,
                    "threshold": max_clients_threshold,
                    "message": "Too many connected clients",
                }
            )

    # Hit rate analysis
    min_hit_rate = config["redis_monitoring"]["thresholds"]["min_hit_rate"]
    total_hits = sum(int(m.get("keyspace_hits", 0)) for m in metrics)
    total_misses = sum(int(m.get("keyspace_misses", 0)) for m in metrics)

    if total_hits + total_misses > 0:
        hit_rate = (total_hits / (total_hits + total_misses)) * 100
        analysis["summary"]["avg_hit_rate"] = hit_rate

        if hit_rate < min_hit_rate:
            analysis["violations"].append(
                {
                    "type": "hit_rate",
                    "value": hit_rate,
                    "threshold": min_hit_rate,
                    "message": "Cache hit rate below threshold",
                }
            )

    # Generate recommendations
    if analysis["summary"]["max_memory_usage"] > max_memory_threshold * 0.8:
        analysis["recommendations"].append(
            "Consider increasing Redis memory or implementing key eviction"
        )

    if analysis["summary"]["max_clients"] > max_clients_threshold * 0.8:
        analysis["recommendations"].append(
            "Monitor client connections and consider connection pooling"
        )

    if analysis["summary"]["avg_hit_rate"] < min_hit_rate * 1.2:
        analysis["recommendations"].append(
            "Review cache key design and TTL settings to improve hit rate"
        )

    analysis["summary"]["threshold_violations"] = len(analysis["violations"])
    return analysis


def main():
    parser = argparse.ArgumentParser(description="Analyze Redis metrics")
    parser.add_argument("--input", required=True, help="Redis metrics log file")
    parser.add_argument("--config", required=True, help="Load test configuration file")
    parser.add_argument("--output", required=True, help="Output analysis file")

    args = parser.parse_args()

    try:
        with open(args.config, "r") as f:
            config = json.load(f)

        metrics = parse_redis_info(args.input)
        analysis = analyze_metrics(metrics, config)

        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)

        if analysis["summary"]["threshold_violations"] > 0:
            print(f"Found {analysis['summary']['threshold_violations']} threshold violations")
            for violation in analysis["violations"]:
                print(f"- {violation['message']}")
            sys.exit(1)

        print("Redis metrics analysis completed successfully")
        sys.exit(0)

    except Exception as e:
        print(f"Error analyzing Redis metrics: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
