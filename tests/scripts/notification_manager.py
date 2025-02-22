#!/usr/bin/env python3
"""
IOTA Notification Manager
Handles multiple notification methods for alerts
"""

import fcntl
import json
import os
import smtplib
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

import requests


class NotificationMethod:
    STDOUT = "stdout"
    FILE = "file"
    EMAIL = "email"
    SLACK = "slack"


class NotificationManager:
    def __init__(self, config_path: str, notification_dir: str):
        self.config_path = config_path
        self.notification_dir = notification_dir
        self.notification_history_file = os.path.join(notification_dir, "notification_history.json")
        self.ensure_dirs()
        self.load_config()

    def ensure_dirs(self):
        """Ensure required directories exist"""
        os.makedirs(self.notification_dir, exist_ok=True)

    def load_config(self) -> Dict:
        """Load notification configuration"""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return self.get_default_config()

    def get_default_config(self) -> Dict:
        """Return default notification configuration"""
        return {
            "methods": {
                "stdout": {"enabled": True},
                "file": {"enabled": True, "path": "alerts.log"},
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_address": "",
                    "to_addresses": [],
                },
                "slack": {"enabled": False, "webhook_url": "", "channel": ""},
            },
            "aggregation": {"enabled": True, "window_seconds": 300, "max_similar": 5},
            "retention_days": 30,
        }

    def should_aggregate(self, alert_data: Dict) -> bool:
        """Check if alert should be aggregated based on history"""
        try:
            if not os.path.exists(self.notification_history_file):
                return False

            config = self.load_config()
            if not config.get("aggregation", {}).get("enabled", False):
                return False

            window = config.get("aggregation", {}).get("window_seconds", 300)
            max_similar = config.get("aggregation", {}).get("max_similar", 5)

            with open(self.notification_history_file, "r") as f:
                history = json.load(f)

            # Check for similar alerts in the time window
            cutoff = time.time() - window
            similar_count = 0

            for entry in history.get("alerts", []):
                if entry.get("timestamp", 0) < cutoff:
                    continue
                if entry.get("metric") == alert_data.get("metric") and entry.get(
                    "level"
                ) == alert_data.get("level"):
                    similar_count += 1

            return similar_count >= max_similar
        except (json.JSONDecodeError, OSError):
            return False

    def update_history(self, alert_data: Dict):
        """Update notification history"""
        try:
            history = {"alerts": []}
            if os.path.exists(self.notification_history_file):
                with open(self.notification_history_file, "r") as f:
                    history = json.load(f)

            # Add timestamp to alert data
            alert_data["timestamp"] = time.time()

            # Add to history
            history.get("alerts", []).append(alert_data)

            # Atomic write with file locking
            temp_file = f"{self.notification_history_file}.tmp"
            with open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(history, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.rename(temp_file, self.notification_history_file)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error updating history: {e}", file=sys.stderr)

    def notify_stdout(self, message: str):
        """Print to stdout"""
        print(message)

    def notify_file(self, message: str, config: Dict):
        """Write to log file"""
        log_path = os.path.join(self.notification_dir, config.get("path", "alerts.log"))
        try:
            with open(log_path, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(f"{datetime.now().isoformat()}: {message}\n")
        except OSError as e:
            print(f"Error writing to log file: {e}", file=sys.stderr)

    def notify_email(self, message: str, config: Dict):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg["From"] = config["from_address"]
            msg["To"] = ", ".join(config["to_addresses"])
            msg["Subject"] = "IOTA Performance Alert"

            msg.attach(MIMEText(message, "plain"))

            with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
                server.starttls()
                server.login(config["username"], config["password"])
                server.send_message(msg)
        except Exception as e:
            print(f"Error sending email: {e}", file=sys.stderr)

    def notify_slack(self, message: str, config: Dict):
        """Send Slack notification"""
        try:
            payload = {"channel": config["channel"], "text": message, "username": "IOTA Monitor"}

            response = requests.post(
                config["webhook_url"], json=payload, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error sending Slack notification: {e}", file=sys.stderr)

    def send_notification(self, alert_data: Dict):
        """Send notification through configured methods"""
        if self.should_aggregate(alert_data):
            return

        config = self.load_config()
        message = f"[{alert_data['level']}] {alert_data['message']}"

        methods = config.get("methods", {})

        # Update history before sending notifications
        self.update_history(alert_data)

        # Send through each enabled method
        if methods.get("stdout", {}).get("enabled", True):
            self.notify_stdout(message)

        if methods.get("file", {}).get("enabled", True):
            self.notify_file(message, methods["file"])

        if methods.get("email", {}).get("enabled", False):
            self.notify_email(message, methods["email"])

        if methods.get("slack", {}).get("enabled", False):
            self.notify_slack(message, methods["slack"])

    def cleanup_old_notifications(self):
        """Remove notifications older than retention period"""
        try:
            if not os.path.exists(self.notification_history_file):
                return

            config = self.load_config()
            retention_days = config.get("retention_days", 30)
            cutoff = time.time() - (retention_days * 24 * 60 * 60)

            with open(self.notification_history_file, "r") as f:
                history = json.load(f)

            # Remove old notifications
            history["alerts"] = [
                alert for alert in history.get("alerts", []) if alert.get("timestamp", 0) > cutoff
            ]

            # Atomic write
            temp_file = f"{self.notification_history_file}.tmp"
            with open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(history, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.rename(temp_file, self.notification_history_file)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error cleaning up notifications: {e}", file=sys.stderr)


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: notification_manager.py <config_file> <notification_dir> <alert_file>",
            file=sys.stderr,
        )
        sys.exit(1)

    config_file = sys.argv[1]
    notification_dir = sys.argv[2]
    alert_file = sys.argv[3]

    try:
        with open(alert_file, "r") as f:
            alert_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading alert data: {e}", file=sys.stderr)
        sys.exit(1)

    manager = NotificationManager(config_file, notification_dir)
    manager.send_notification(alert_data)
    manager.cleanup_old_notifications()


if __name__ == "__main__":
    main()
