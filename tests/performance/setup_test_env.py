#!/usr/bin/env python3
"""Setup test environment for IOTA rate limiter performance testing."""
import argparse
import json
import os
import subprocess
import sys
import time
from typing import Dict, Optional, Tuple

import redis


def check_redis_connection(
    host: str = "localhost", port: int = 6379, timeout: int = 5
) -> Tuple[bool, Optional[str]]:
    """Check if Redis is running and accessible."""
    try:
        client = redis.Redis(
            host=host, port=port, socket_connect_timeout=timeout, decode_responses=True
        )
        client.ping()
        info = client.info()
        return True, f"Redis v{info['redis_version']} running on {host}:{port}"
    except redis.ConnectionError as e:
        return False, f"Redis connection failed: {e}"
    except Exception as e:
        return False, f"Unexpected Redis error: {e}"


def check_app_server(
    host: str = "localhost", port: int = 8001, timeout: int = 5
) -> Tuple[bool, Optional[str]]:
    """Check if the application server is running."""
    import requests

    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=timeout)
        return response.status_code == 200, "Application server is running"
    except requests.ConnectionError:
        return False, "Application server is not running"
    except Exception as e:
        return False, f"Unexpected server error: {e}"


def load_test_data(redis_client: redis.Redis, config_file: str) -> Tuple[bool, Optional[str]]:
    """Load test data into Redis."""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)

        # Load test rate limits
        for endpoint in config.get("endpoints", {}).keys():
            key = f"rate_limit:{endpoint}"
            redis_client.hset(key, mapping={"window": 60, "max_requests": 1000, "remaining": 1000})

        return True, "Test data loaded successfully"
    except Exception as e:
        return False, f"Failed to load test data: {e}"


def setup_environment(config_file: str) -> Dict[str, Dict]:
    """Setup and validate test environment."""
    status = {
        "redis": {"running": False, "message": None},
        "app_server": {"running": False, "message": None},
        "test_data": {"loaded": False, "message": None},
    }

    # Check Redis
    status["redis"]["running"], status["redis"]["message"] = check_redis_connection()

    # If Redis is running, load test data
    if status["redis"]["running"]:
        redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        status["test_data"]["loaded"], status["test_data"]["message"] = load_test_data(
            redis_client, config_file
        )

    # Check application server
    status["app_server"]["running"], status["app_server"]["message"] = check_app_server()

    return status


def print_status(status: Dict[str, Dict]) -> None:
    """Print environment status in a formatted way."""
    print("\nTest Environment Status:")
    print("------------------------")

    # Redis Status
    print("\n1. Redis Server:")
    print(f"   Status: {'✓' if status['redis']['running'] else '✗'}")
    print(f"   Details: {status['redis']['message']}")

    # Test Data Status
    print("\n2. Test Data:")
    print(f"   Status: {'✓' if status['test_data']['loaded'] else '✗'}")
    print(f"   Details: {status['test_data']['message']}")

    # Application Server Status
    print("\n3. Application Server:")
    print(f"   Status: {'✓' if status['app_server']['running'] else '✗'}")
    print(f"   Details: {status['app_server']['message']}")

    # Overall Status
    all_running = all(
        [status["redis"]["running"], status["test_data"]["loaded"], status["app_server"]["running"]]
    )
    print("\nOverall Status:")
    print(f"{'✓ Ready for testing' if all_running else '✗ Environment setup incomplete'}")


def main():
    parser = argparse.ArgumentParser(
        description="Setup test environment for rate limiter performance testing"
    )
    parser.add_argument("--config", required=True, help="Load test configuration file")

    args = parser.parse_args()

    try:
        # Check environment
        status = setup_environment(args.config)
        print_status(status)

        # Exit with status
        all_running = all(
            [
                status["redis"]["running"],
                status["test_data"]["loaded"],
                status["app_server"]["running"],
            ]
        )
        sys.exit(0 if all_running else 1)

    except Exception as e:
        print(f"Error setting up test environment: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
