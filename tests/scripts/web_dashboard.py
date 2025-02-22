#!/usr/bin/env python3
"""IOTA Performance Monitoring Dashboard

A Flask-based web dashboard for real-time monitoring of IOTA performance metrics
and alerts. Provides visualization, configuration management, and alert history.
"""

import glob
import hashlib
import json
import logging
import os
import queue
import secrets
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secure secret key for sessions
metrics_queue = queue.Queue()
alert_queue = queue.Queue()

# Rate limiting configuration
RATE_LIMIT_WINDOW = 300  # 5 minutes
MAX_REQUESTS = 100  # Maximum requests per window
MAX_LOGIN_ATTEMPTS = 5  # Maximum failed login attempts
LOGIN_BLOCK_DURATION = 900  # 15 minutes block after max attempts

# Rate limiting storage
request_counts = defaultdict(list)  # IP -> [(timestamp, count)]
failed_logins = defaultdict(list)  # IP -> [(timestamp, count)]

# User management configuration
USER_ROLES = ["admin", "user", "readonly"]
PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIRES = {"uppercase": True, "lowercase": True, "numbers": True, "special": True}
PASSWORD_RESET_EXPIRY = 3600  # 1 hour

# Password reset storage
password_reset_tokens = {}  # token -> (username, expiry)


def setup_logging():
    """Configure logging with proper format and handlers"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("dashboard.log"), logging.StreamHandler()],
    )
    return logging.getLogger("iota_dashboard")


logger = setup_logging()


def audit_log(event_type: str, user: str, ip: str, details: str, success: bool):
    """Log security-relevant events"""
    logger.info(
        f"AUDIT: {event_type} | User: {user} | IP: {ip} | "
        f"Success: {success} | Details: {details}"
    )


def check_rate_limit(ip: str) -> Tuple[bool, int]:
    """Check if IP has exceeded rate limit"""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    request_counts[ip] = [(ts, count) for ts, count in request_counts[ip] if ts > window_start]

    # Count requests in window
    total = sum(count for _, count in request_counts[ip])

    if total >= MAX_REQUESTS:
        return False, int(min(ts for ts, _ in request_counts[ip]) + RATE_LIMIT_WINDOW - now)

    request_counts[ip].append((now, 1))
    return True, 0


def check_login_attempts(ip: str) -> Tuple[bool, int]:
    """Check if IP has exceeded failed login attempts"""
    now = time.time()
    block_start = now - LOGIN_BLOCK_DURATION

    # Clean old entries
    failed_logins[ip] = [(ts, count) for ts, count in failed_logins[ip] if ts > block_start]

    # Count failed attempts
    total = sum(count for _, count in failed_logins[ip])

    if total >= MAX_LOGIN_ATTEMPTS:
        return False, int(min(ts for ts, _ in failed_logins[ip]) + LOGIN_BLOCK_DURATION - now)

    return True, 0


def rate_limit(f):
    """Decorator to apply rate limiting to routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        allowed, wait_time = check_rate_limit(ip)

        if not allowed:
            audit_log(
                "RATE_LIMIT",
                session.get("username", "anonymous"),
                ip,
                f"Rate limit exceeded. Wait time: {wait_time}s",
                False,
            )
            return jsonify({"error": "Rate limit exceeded", "wait_seconds": wait_time}), 429

        return f(*args, **kwargs)

    return decorated_function


def check_password_strength(password: str) -> Tuple[bool, str]:
    """Check if password meets security requirements"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"

    if PASSWORD_REQUIRES["uppercase"] and not any(c.isupper() for c in password):
        return False, "Password must contain uppercase letters"

    if PASSWORD_REQUIRES["lowercase"] and not any(c.islower() for c in password):
        return False, "Password must contain lowercase letters"

    if PASSWORD_REQUIRES["numbers"] and not any(c.isdigit() for c in password):
        return False, "Password must contain numbers"

    if PASSWORD_REQUIRES["special"] and not any(not c.isalnum() for c in password):
        return False, "Password must contain special characters"

    return True, ""


def load_users() -> Dict[str, Dict]:
    """Load users from config file with roles"""
    try:
        with open("dashboard_users.json") as f:
            users = json.load(f)
            # Migrate old format if needed
            if not isinstance(next(iter(users.values())), dict):
                users = {
                    username: {
                        "password": password_hash,
                        "role": "admin" if username == "admin" else "user",
                    }
                    for username, password_hash in users.items()
                }
                with open("dashboard_users.json", "w") as f:
                    json.dump(users, f, indent=2)
            return users
    except FileNotFoundError:
        # Create default admin user if no config exists
        users = {
            "admin": {
                "password": generate_password_hash("admin", method="pbkdf2:sha256"),
                "role": "admin",
            }
        }
        with open("dashboard_users.json", "w") as f:
            json.dump(users, f, indent=2)
        return users


USERS = load_users()


def requires_role(roles: List[str]):
    """Decorator to require specific roles for routes"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = session.get("username")
            if not username or USERS[username]["role"] not in roles:
                audit_log(
                    "UNAUTHORIZED_ACCESS",
                    username or "anonymous",
                    request.remote_addr,
                    f"Attempted to access route requiring roles: {roles}",
                    False,
                )
                return jsonify({"error": "Unauthorized"}), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def login_required(f):
    """Decorator to require login for routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def csrf_token() -> str:
    """Generate or return existing CSRF token"""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def check_csrf():
    """Verify CSRF token"""
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token or token != session.get("csrf_token"):
        return False
    return True


class DashboardManager:
    def __init__(self, metrics_dir: str, alerts_dir: str):
        self.metrics_dir = metrics_dir
        self.alerts_dir = alerts_dir

    def get_recent_metrics(self, hours: int = 24) -> List[Dict]:
        """Get metrics from the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        metrics = []
        try:
            pattern = os.path.join(self.metrics_dir, "metrics_*.json")
            for file in glob.glob(pattern):
                if os.path.getmtime(file) > cutoff.timestamp():
                    with open(file) as f:
                        metrics.append(json.load(f))
        except Exception as e:
            logger.error(f"Error reading metrics: {e}")
        return metrics

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get alerts from the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        alerts = []
        try:
            pattern = os.path.join(self.alerts_dir, "alert_*.json")
            for file in glob.glob(pattern):
                if os.path.getmtime(file) > cutoff.timestamp():
                    with open(file) as f:
                        alerts.append(json.load(f))
        except Exception as e:
            logger.error(f"Error reading alerts: {e}")
        return alerts


# Initialize dashboard with default paths
dashboard = DashboardManager(metrics_dir="/tmp/iota_metrics", alerts_dir="/tmp/iota_alerts")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    ip = request.remote_addr

    if request.method == "POST":
        allowed, wait_time = check_login_attempts(ip)
        if not allowed:
            audit_log(
                "LOGIN_BLOCKED",
                request.form.get("username", "unknown"),
                ip,
                f"Too many failed attempts. Wait time: {wait_time}s",
                False,
            )
            return render_template(
                "login.html",
                error=f"Too many failed attempts. Please try again in {wait_time} seconds.",
            )

        username = request.form["username"]
        password = request.form["password"]

        if username in USERS and check_password_hash(USERS[username]["password"], password):
            session["username"] = username
            session["csrf_token"] = secrets.token_hex(32)
            audit_log("LOGIN", username, ip, "Successful login", True)
            return redirect(url_for("index"))

        # Record failed login attempt
        failed_logins[ip].append((time.time(), 1))
        audit_log("LOGIN_FAILED", username, ip, "Invalid credentials", False)
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Handle user logout"""
    username = session.get("username", "anonymous")
    ip = request.remote_addr
    audit_log("LOGOUT", username, ip, "User logged out", True)
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
@rate_limit
def index():
    """Render main dashboard page"""
    return render_template("dashboard.html", csrf_token=csrf_token())


@app.route("/api/metrics/recent")
@login_required
@rate_limit
def recent_metrics():
    """Get recent metrics as JSON"""
    try:
        hours = request.args.get("hours", 24, type=int)
        metrics = dashboard.get_recent_metrics(hours)
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts/recent")
@login_required
@rate_limit
def recent_alerts():
    """Get recent alerts as JSON"""
    try:
        hours = request.args.get("hours", 24, type=int)
        alerts = dashboard.get_recent_alerts(hours)
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/config", methods=["GET", "POST"])
@login_required
@rate_limit
def manage_config():
    """Get or update notification configuration"""
    if request.method == "POST":
        if not check_csrf():
            audit_log(
                "CSRF_FAILURE",
                session.get("username"),
                request.remote_addr,
                "Invalid CSRF token on config update",
                False,
            )
            return jsonify({"error": "Invalid CSRF token"}), 403

        try:
            new_config = request.get_json()
            with open("notification_config.json", "w") as f:
                json.dump(new_config, f, indent=2)
            audit_log(
                "CONFIG_UPDATE",
                session.get("username"),
                request.remote_addr,
                "Configuration updated successfully",
                True,
            )
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            audit_log(
                "CONFIG_UPDATE_FAILED",
                session.get("username"),
                request.remote_addr,
                f"Error: {str(e)}",
                False,
            )
            return jsonify({"error": str(e)}), 500
    else:
        try:
            with open("notification_config.json") as f:
                return jsonify(json.load(f))
        except Exception as e:
            logger.error(f"Error reading config: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/users", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
@requires_role(["admin"])
@rate_limit
def manage_users():
    """Manage users (admin only)"""
    if not check_csrf():
        return jsonify({"error": "Invalid CSRF token"}), 403

    if request.method == "GET":
        # Return user list without passwords
        return jsonify({username: {"role": data["role"]} for username, data in USERS.items()})

    elif request.method == "POST":
        # Create new user
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "user")

        if not username or not password or role not in USER_ROLES:
            return jsonify({"error": "Invalid user data"}), 400

        if username in USERS:
            return jsonify({"error": "User already exists"}), 409

        valid, msg = check_password_strength(password)
        if not valid:
            return jsonify({"error": msg}), 400

        USERS[username] = {
            "password": generate_password_hash(password, method="pbkdf2:sha256"),
            "role": role,
        }

        with open("dashboard_users.json", "w") as f:
            json.dump(USERS, f, indent=2)

        audit_log(
            "USER_CREATED",
            session["username"],
            request.remote_addr,
            f"Created user: {username} with role: {role}",
            True,
        )
        return jsonify({"status": "success"})

    elif request.method == "PUT":
        # Update user
        data = request.get_json()
        username = data.get("username")
        new_password = data.get("password")
        new_role = data.get("role")

        if username not in USERS:
            return jsonify({"error": "User not found"}), 404

        if new_password:
            valid, msg = check_password_strength(new_password)
            if not valid:
                return jsonify({"error": msg}), 400
            USERS[username]["password"] = generate_password_hash(
                new_password, method="pbkdf2:sha256"
            )

        if new_role and new_role in USER_ROLES:
            USERS[username]["role"] = new_role

        with open("dashboard_users.json", "w") as f:
            json.dump(USERS, f, indent=2)

        audit_log(
            "USER_UPDATED",
            session["username"],
            request.remote_addr,
            f"Updated user: {username}",
            True,
        )
        return jsonify({"status": "success"})

    elif request.method == "DELETE":
        # Delete user
        username = request.args.get("username")
        if not username or username == "admin":
            return jsonify({"error": "Cannot delete admin user"}), 400

        if username not in USERS:
            return jsonify({"error": "User not found"}), 404

        del USERS[username]
        with open("dashboard_users.json", "w") as f:
            json.dump(USERS, f, indent=2)

        audit_log(
            "USER_DELETED",
            session["username"],
            request.remote_addr,
            f"Deleted user: {username}",
            True,
        )
        return jsonify({"status": "success"})


@app.route("/api/users/reset-password", methods=["POST"])
@rate_limit
def request_password_reset():
    """Request a password reset"""
    if not check_csrf():
        return jsonify({"error": "Invalid CSRF token"}), 403

    data = request.get_json()
    username = data.get("username")

    if not username or username not in USERS:
        # Don't reveal if user exists
        return jsonify({"status": "success"})

    # Generate reset token
    token = secrets.token_urlsafe(32)
    expiry = time.time() + PASSWORD_RESET_EXPIRY
    password_reset_tokens[token] = (username, expiry)

    # In a real system, send this via email
    # For now, just return it (THIS IS NOT SECURE - DEMO ONLY)
    audit_log(
        "PASSWORD_RESET_REQUESTED",
        username,
        request.remote_addr,
        "Password reset token generated",
        True,
    )
    return jsonify({"status": "success", "token": token, "expires_in": PASSWORD_RESET_EXPIRY})


@app.route("/api/users/reset-password/<token>", methods=["POST"])
@rate_limit
def reset_password(token):
    """Reset password using token"""
    if token not in password_reset_tokens:
        return jsonify({"error": "Invalid or expired token"}), 400

    username, expiry = password_reset_tokens[token]
    if time.time() > expiry:
        del password_reset_tokens[token]
        return jsonify({"error": "Token expired"}), 400

    data = request.get_json()
    new_password = data.get("password")

    valid, msg = check_password_strength(new_password)
    if not valid:
        return jsonify({"error": msg}), 400

    USERS[username]["password"] = generate_password_hash(new_password, method="pbkdf2:sha256")

    with open("dashboard_users.json", "w") as f:
        json.dump(USERS, f, indent=2)

    del password_reset_tokens[token]

    audit_log(
        "PASSWORD_RESET_COMPLETE", username, request.remote_addr, "Password reset successful", True
    )
    return jsonify({"status": "success"})


def start_dashboard(host: str = "127.0.0.1", port: int = 5000, ssl_context: Optional[tuple] = None):
    """Start the dashboard server with optional SSL"""
    app.run(host=host, port=port, ssl_context=ssl_context, debug=False)


if __name__ == "__main__":
    # Check if SSL certificates exist
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        ssl_context = ("cert.pem", "key.pem")
    else:
        ssl_context = None
        logger.warning("SSL certificates not found, running in HTTP mode")

    start_dashboard(ssl_context=ssl_context)
