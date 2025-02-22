#!/usr/bin/env python3
"""
IOTA Alert Manager
Handles alert threshold configuration and real-time monitoring
"""

import fcntl
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class AlertLevel:
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertManager:
    def __init__(self, config_path: str, alert_dir: str):
        self.config_path = config_path
        self.alert_dir = alert_dir
        self.alert_history_file = os.path.join(alert_dir, "alert_history.json")
        self.ensure_dirs()
        self.load_config()

    def ensure_dirs(self):
        """Ensure required directories exist"""
        os.makedirs(self.alert_dir, exist_ok=True)

    def load_config(self) -> Dict:
        """Load alert configuration"""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return self.get_default_config()

    def get_default_config(self) -> Dict:
        """Return default alert configuration"""
        return {
            "thresholds": {
                "memory_percent": {"warning": 80.0, "critical": 90.0},
                "cpu_percent": {"warning": 70.0, "critical": 85.0},
                "disk_percent": {"warning": 85.0, "critical": 95.0},
            },
            "alert_retention_days": 30,
            "throttle_seconds": 300,  # 5 minutes between repeated alerts
        }

    def check_metric(self, metric_name: str, value: float) -> Optional[Tuple[str, str]]:
        """
        Check if metric exceeds thresholds
        Returns (level, message) if threshold exceeded, None otherwise
        """
        config = self.load_config()
        thresholds = config.get("thresholds", {}).get(metric_name)

        if not thresholds:
            return None

        if value >= thresholds.get("critical", float("inf")):
            return (
                AlertLevel.CRITICAL,
                f"{metric_name} is CRITICAL: {value:.1f} (threshold: {thresholds['critical']})",
            )

        if value >= thresholds.get("warning", float("inf")):
            return (
                AlertLevel.WARNING,
                f"{metric_name} is WARNING: {value:.1f} (threshold: {thresholds['warning']})",
            )

        return None

    def should_throttle(self, metric_name: str, level: str) -> bool:
        """Check if alert should be throttled based on history"""
        try:
            if not os.path.exists(self.alert_history_file):
                return False

            with open(self.alert_history_file, "r") as f:
                history = json.load(f)

            config = self.load_config()
            throttle_seconds = config.get("throttle_seconds", 300)

            key = f"{metric_name}:{level}"
            last_alert = history.get(key, 0)

            return (time.time() - last_alert) < throttle_seconds
        except (json.JSONDecodeError, OSError):
            return False

    def update_alert_history(self, metric_name: str, level: str):
        """Update alert history with latest alert time"""
        try:
            history = {}
            if os.path.exists(self.alert_history_file):
                with open(self.alert_history_file, "r") as f:
                    history = json.load(f)

            key = f"{metric_name}:{level}"
            history[key] = time.time()

            # Atomic write with file locking
            temp_file = f"{self.alert_history_file}.tmp"
            with open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(history, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.rename(temp_file, self.alert_history_file)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error updating alert history: {e}", file=sys.stderr)

    def send_alert(self, metric_name: str, level: str, message: str):
        """Send alert through notification system"""
        alert_data = {
            "metric": metric_name,
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Write alert data to temporary file
        alert_file = os.path.join(self.alert_dir, "current_alert.json")
        try:
            with open(alert_file, "w") as f:
                json.dump(alert_data, f)

            # Send through notification manager if available
            if os.path.exists("./notification_manager.py"):
                os.system(
                    f'python3 ./notification_manager.py "./notification_config.json" "{self.alert_dir}" "{alert_file}"'
                )
        except OSError as e:
            print(f"Error sending alert: {e}", file=sys.stderr)

    def check_metrics(self, metrics: Dict[str, float]) -> List[Tuple[str, str, str]]:
        """
        Check all metrics against thresholds
        Returns list of (metric_name, level, message) for exceeded thresholds
        """
        alerts = []
        for metric_name, value in metrics.items():
            result = self.check_metric(metric_name, value)
            if result:
                level, message = result
                if not self.should_throttle(metric_name, level):
                    self.update_alert_history(metric_name, level)
                    alerts.append((metric_name, level, message))
                    # Send alert through notification system
                    self.send_alert(metric_name, level, message)
        return alerts

    def cleanup_old_alerts(self):
        """Remove alerts older than retention period"""
        try:
            if not os.path.exists(self.alert_history_file):
                return

            config = self.load_config()
            retention_days = config.get("alert_retention_days", 30)
            cutoff = time.time() - (retention_days * 24 * 60 * 60)

            with open(self.alert_history_file, "r") as f:
                history = json.load(f)

            # Remove old alerts
            history = {k: v for k, v in history.items() if v > cutoff}

            # Atomic write
            temp_file = f"{self.alert_history_file}.tmp"
            with open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(history, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.rename(temp_file, self.alert_history_file)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error cleaning up alerts: {e}", file=sys.stderr)


def main():
    if len(sys.argv) != 4:
        print("Usage: alert_manager.py <config_file> <alert_dir> <metrics_file>", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    alert_dir = sys.argv[2]
    metrics_file = sys.argv[3]

    try:
        with open(metrics_file, "r") as f:
            metrics = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading metrics: {e}", file=sys.stderr)
        sys.exit(1)

    manager = AlertManager(config_file, alert_dir)

    # Convert string values to float where needed
    processed_metrics = {}
    for k, v in metrics.items():
        if k.endswith("_percent") or k.endswith("_mb"):
            try:
                processed_metrics[k] = float(v)
            except (ValueError, TypeError):
                print(f"Warning: Could not convert {k}={v} to float", file=sys.stderr)

    alerts = manager.check_metrics(processed_metrics)

    if alerts:
        print("\n=== Alert Report ===")
        for metric, level, message in alerts:
            print(f"[{level}] {message}")

    manager.cleanup_old_alerts()


if __name__ == "__main__":
    main()
