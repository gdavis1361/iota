#!/usr/bin/env python3
"""
IOTA Metric Storage Module
Handles persistent storage of benchmark metrics
"""

import fcntl
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict


class MetricStore:
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()

    def ensure_storage_dir(self):
        """Ensure storage directory exists"""
        os.makedirs(self.storage_dir, exist_ok=True)

    def store_metrics(self, metrics: Dict[str, Any]) -> str:
        """
        Store metrics in a JSON file with timestamp
        Returns the path to the stored metrics file
        """
        # Ensure timestamp exists
        if "timestamp" not in metrics:
            metrics["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Generate filename based on timestamp
        filename = f"metrics_{metrics['timestamp'].replace(':', '-').replace('+', '-')}.json"
        filepath = os.path.join(self.storage_dir, filename)

        # Atomic write with file locking
        temp_path = filepath + ".tmp"
        try:
            with open(temp_path, "w") as f:
                # Get exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(metrics, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            os.rename(temp_path, filepath)
            return filepath
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

    def cleanup_old_metrics(self, days: int = 30) -> int:
        """
        Remove metrics older than specified days
        Returns number of files removed
        """
        cutoff = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
        removed = 0

        for filename in os.listdir(self.storage_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.storage_dir, filename)
            try:
                if os.path.getmtime(filepath) < cutoff:
                    os.unlink(filepath)
                    removed += 1
            except OSError as e:
                print(f"Warning: Could not remove {filepath}: {e}", file=sys.stderr)

        return removed

    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get the most recent metrics"""
        latest_file = None
        latest_time = 0

        for filename in os.listdir(self.storage_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.storage_dir, filename)
            file_time = os.path.getmtime(filepath)

            if file_time > latest_time:
                latest_time = file_time
                latest_file = filepath

        if latest_file:
            try:
                with open(latest_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Error reading {latest_file}: {e}", file=sys.stderr)

        return {}


def main():
    if len(sys.argv) < 3:
        print("Usage: store_metrics.py <storage_directory> <metrics_json>", file=sys.stderr)
        sys.exit(1)

    storage_dir = sys.argv[1]
    metrics_json = sys.argv[2]

    try:
        with open(metrics_json, "r") as f:
            metrics = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading metrics file: {e}", file=sys.stderr)
        sys.exit(1)

    store = MetricStore(storage_dir)
    filepath = store.store_metrics(metrics)
    print(f"Metrics stored in: {filepath}")

    # Cleanup old metrics (30 days)
    removed = store.cleanup_old_metrics()
    if removed:
        print(f"Cleaned up {removed} old metric files")


if __name__ == "__main__":
    main()
