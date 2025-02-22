import time
from typing import Dict, Optional

import sentry_sdk
from app.core.config import settings
from prometheus_client import Counter, Gauge, Histogram

# Prometheus metrics
RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total", "Total number of rate limit exceeded events", ["endpoint", "ip"]
)

RATE_LIMIT_REMAINING = Gauge(
    "rate_limit_remaining", "Number of requests remaining in the current window", ["endpoint", "ip"]
)

RATE_LIMIT_WINDOW_RESET = Gauge(
    "rate_limit_window_reset_seconds",
    "Seconds until the rate limit window resets",
    ["endpoint", "ip"],
)

FAILED_LOGIN_ATTEMPTS = Counter(
    "failed_login_attempts_total", "Total number of failed login attempts", ["ip"]
)

REQUEST_DURATION = Histogram(
    "rate_limit_check_duration_seconds", "Time spent checking rate limits", ["endpoint"]
)


class RateLimitMonitor:
    def __init__(self):
        self.sentry_enabled = bool(settings.SENTRY_DSN)

    def record_rate_limit_exceeded(
        self, endpoint: str, ip: str, wait_time: int, remaining: int, reset_time: int
    ) -> None:
        """Record a rate limit exceeded event"""
        # Update Prometheus metrics
        RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint, ip=ip).inc()
        RATE_LIMIT_REMAINING.labels(endpoint=endpoint, ip=ip).set(remaining)
        RATE_LIMIT_WINDOW_RESET.labels(endpoint=endpoint, ip=ip).set(reset_time)

        # Send to Sentry if enabled
        if self.sentry_enabled:
            sentry_sdk.capture_message(
                "Rate limit exceeded",
                level="warning",
                extras={
                    "endpoint": endpoint,
                    "ip": ip,
                    "wait_time": wait_time,
                    "remaining": remaining,
                    "reset_time": reset_time,
                },
            )

    def record_failed_login(self, ip: str) -> None:
        """Record a failed login attempt"""
        FAILED_LOGIN_ATTEMPTS.labels(ip=ip).inc()

        if self.sentry_enabled:
            sentry_sdk.capture_message("Failed login attempt", level="warning", extras={"ip": ip})

    def record_request_duration(self, endpoint: str, duration: float) -> None:
        """Record the duration of a rate limit check"""
        REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

    def update_rate_limit_metrics(
        self, endpoint: str, ip: str, remaining: int, reset_time: int
    ) -> None:
        """Update rate limit metrics for an endpoint"""
        RATE_LIMIT_REMAINING.labels(endpoint=endpoint, ip=ip).set(remaining)
        RATE_LIMIT_WINDOW_RESET.labels(endpoint=endpoint, ip=ip).set(reset_time)


class RateLimitMetricsMiddleware:
    """Middleware to track rate limit metrics"""

    def __init__(self, monitor: RateLimitMonitor):
        self.monitor = monitor

    def __call__(
        self, start_time: float, endpoint: str, ip: str, remaining: int, reset_time: int
    ) -> None:
        """Record metrics for a rate limit check"""
        duration = time.time() - start_time
        self.monitor.record_request_duration(endpoint, duration)
        self.monitor.update_rate_limit_metrics(endpoint, ip, remaining, reset_time)
