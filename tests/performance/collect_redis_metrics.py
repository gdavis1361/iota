#!/usr/bin/env python3
"""Collect Redis metrics during performance testing."""
import argparse
import json
import sys
import time
from typing import Dict, List

import redis


def collect_metrics(redis_client: redis.Redis, metrics: List[str]) -> Dict:
    """Collect specified metrics from Redis INFO."""
    info = redis_client.info()
    return {metric: info.get(metric, 0) for metric in metrics}


def main():
    parser = argparse.ArgumentParser(description="Collect Redis metrics")
    parser.add_argument("--config", required=True, help="Load test configuration file")
    parser.add_argument("--output", required=True, help="Output log file")
    parser.add_argument(
        "--duration", type=int, required=True, help="Collection duration in seconds"
    )
    parser.add_argument("--host", default="localhost", help="Redis host")
    parser.add_argument("--port", type=int, default=6379, help="Redis port")

    args = parser.parse_args()

    try:
        # Load configuration
        with open(args.config, "r") as f:
            config = json.load(f)

        # Connect to Redis
        try:
            redis_client = redis.Redis(
                host=args.host, port=args.port, decode_responses=True, socket_connect_timeout=5
            )
            # Test connection
            redis_client.ping()
        except redis.ConnectionError as e:
            print(f"Error connecting to Redis at {args.host}:{args.port}: {e}", file=sys.stderr)
            sys.exit(1)

        # Get metrics list from config
        metrics = config["redis_monitoring"].get(
            "metrics",
            [
                "used_memory",
                "used_memory_peak",
                "connected_clients",
                "total_commands_processed",
                "keyspace_hits",
                "keyspace_misses",
            ],
        )

        # Collect metrics at specified interval
        interval = config["redis_monitoring"].get("sample_interval", 60)
        end_time = time.time() + args.duration

        print(f"Starting Redis metrics collection for {args.duration} seconds...")

        with open(args.output, "w") as f:
            while time.time() < end_time:
                try:
                    metric_data = collect_metrics(redis_client, metrics)
                    f.write(json.dumps(metric_data) + "\n")
                    f.flush()
                    print(".", end="", flush=True)
                except redis.RedisError as e:
                    print(f"\nError collecting Redis metrics: {e}", file=sys.stderr)

                time.sleep(interval)

        print("\nRedis metrics collection completed")

    except Exception as e:
        print(f"Error in metrics collection: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
