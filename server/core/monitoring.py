"""
Monitoring utilities for dynamic sampling and performance tracking.
"""

import contextlib
import time
from threading import Lock
from typing import Any, Dict, Optional

import structlog

from server.core.config import get_settings
from server.core.metrics_storage import MetricsStorage

logger = structlog.get_logger(__name__)


class PerformanceMonitor:
    """Monitor performance of critical operations."""

    _instance: Optional["PerformanceMonitor"] = None
    _lock = Lock()

    def __init__(self, storage: Optional[MetricsStorage] = None):
        """Initialize the monitor with optional storage."""
        self.settings = get_settings()
        self.storage = storage or MetricsStorage()
        self.slow_threshold_ms = self.settings.SLOW_REQUEST_THRESHOLD_MS
        self._lock = Lock()

    @classmethod
    def get_instance(cls) -> "PerformanceMonitor":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Create instance with test settings if in test environment
                    settings = get_settings()
                    if settings.ENVIRONMENT.value == "testing":
                        storage = MetricsStorage(":memory:")  # Use in-memory SQLite for tests
                    else:
                        storage = MetricsStorage()
                    cls._instance = cls(storage)
        return cls._instance

    @contextlib.contextmanager
    def monitor(self, operation: str):
        """Context manager to monitor an operation."""
        start_time = time.perf_counter_ns()
        error = False
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            duration = (time.perf_counter_ns() - start_time) / 1_000_000  # Convert to milliseconds
            self.storage.insert_metric(
                operation, duration=duration, error=error, is_slow=duration > self.slow_threshold_ms
            )

    def _get_time(self) -> float:
        """Get current time, allows for easier mocking in tests."""
        return float(time.time())

    def _should_reset_counters(self) -> bool:
        """Check if we should reset counters based on sampling window."""
        current_time = self._get_time()
        return (current_time - self.last_reset) > self.sampling_window

    def _reset_counters(self):
        """Reset performance counters."""
        self.error_count = 0
        self.request_count = 0
        self.slow_request_count = 0
        self.last_reset = self._get_time()

    def _calculate_new_sample_rates(self) -> Dict[str, float]:
        """Calculate new sampling rates based on metrics."""
        if self.request_count == 0:
            return {"traces": self.current_traces_rate, "profiles": self.current_profiles_rate}

        error_rate = self.error_count / self.request_count
        slow_rate = self.slow_request_count / self.request_count

        # Increase sampling if we're seeing issues
        if error_rate > self.error_rate_threshold or slow_rate > self.slow_rate_threshold:
            return {
                "traces": min(1.0, self.current_traces_rate * 2),
                "profiles": min(1.0, self.current_profiles_rate * 2),
            }

        # Decrease sampling if everything looks good
        if error_rate < (self.error_rate_threshold / 10) and slow_rate < (
            self.slow_rate_threshold / 10
        ):
            return {
                "traces": max(0.01, self.current_traces_rate * 0.5),
                "profiles": max(0.01, self.current_profiles_rate * 0.5),
            }

        # Keep current rates
        return {"traces": self.current_traces_rate, "profiles": self.current_profiles_rate}

    def record_request(self, duration_ms: float, had_error: bool = False):
        """Record a request and its metrics."""
        with self._lock:
            # Check for reset before incrementing counters
            should_reset = self._should_reset_counters()

            # Calculate new rates before reset if needed
            if should_reset:
                new_rates = self._calculate_new_sample_rates()
                error_rate = self.error_count / max(1, self.request_count)
                slow_rate = self.slow_request_count / max(1, self.request_count)
                self._reset_counters()

                # Update rates if they changed
                if (
                    new_rates["traces"] != self.current_traces_rate
                    or new_rates["profiles"] != self.current_profiles_rate
                ):
                    self.current_traces_rate = new_rates["traces"]
                    self.current_profiles_rate = new_rates["profiles"]
                    logger.info(
                        "Updated sampling rates",
                        traces_rate=self.current_traces_rate,
                        profiles_rate=self.current_profiles_rate,
                        error_rate=error_rate,
                        slow_rate=slow_rate,
                    )

            # Now increment counters
            self.request_count += 1
            if had_error:
                self.error_count += 1
            if duration_ms > self.slow_threshold_ms:
                self.slow_request_count += 1

    def record_version_bump(self, duration_ms: float, had_error: bool = False):
        """Record metrics for version bump operation."""
        self.storage.insert_metric(
            "version_bump",
            duration=duration_ms,
            error=had_error,
            is_slow=duration_ms > self.slow_threshold_ms,
        )

    def record_changelog_update(self, duration_ms: float, had_error: bool = False):
        """Record metrics for changelog update operation."""
        self.storage.insert_metric(
            "changelog_update",
            duration=duration_ms,
            error=had_error,
            is_slow=duration_ms > self.slow_threshold_ms,
        )

    def record_hook_installation(self, duration_ms: float, had_error: bool = False):
        """Record metrics for Git hook installation."""
        self.storage.insert_metric(
            "hook_installation",
            duration=duration_ms,
            error=had_error,
            is_slow=duration_ms > self.slow_threshold_ms,
        )

    def get_current_sample_rates(self) -> Dict[str, float]:
        """Get current sampling rates."""
        return {"traces": self.current_traces_rate, "profiles": self.current_profiles_rate}

    def get_version_metrics(self) -> Dict[str, Any]:
        """Get current version management metrics."""
        with self._lock:
            # Get metrics from persistent storage
            summary = self.storage.get_summary(category="version_management")

            # If no persisted metrics, return in-memory metrics
            if not summary:
                return {
                    "version_bump": {
                        "count": self.version_bump_count,
                        "errors": self.version_bump_errors,
                        "avg_duration": self.version_bump_duration_total
                        / max(1, self.version_bump_count),
                    },
                    "changelog": {
                        "count": self.changelog_updates,
                        "errors": self.changelog_errors,
                        "avg_duration": self.changelog_duration_total
                        / max(1, self.changelog_updates),
                    },
                    "hooks": {
                        "count": self.hook_installations,
                        "errors": self.hook_errors,
                        "avg_duration": self.hook_duration_total / max(1, self.hook_installations),
                    },
                }

            return {
                "version_bump": summary.get("version_bump", {}),
                "changelog": summary.get("changelog_update", {}),
                "hooks": summary.get("hook_installation", {}),
            }

    def get_metrics(self, operation: str, window_seconds: Optional[int] = None):
        """Get metrics for an operation within the specified time window."""
        window = window_seconds or self.settings.SAMPLING_WINDOW_SECONDS
        return self.storage.get_metrics_in_window(operation, window)

    def get_aggregated_stats(self, operation: str, window_seconds: Optional[int] = None):
        """Get aggregated statistics for an operation."""
        window = window_seconds or self.settings.SAMPLING_WINDOW_SECONDS
        return self.storage.get_aggregated_stats(operation, window)

    def cleanup_old_metrics(self, window_seconds: Optional[int] = None):
        """Clean up metrics older than the specified window."""
        window = window_seconds or self.settings.SAMPLING_WINDOW_SECONDS
        self.storage.cleanup_old_metrics(window)

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (primarily for testing)."""
        cls._instance = None


# Initialize the monitor
settings = get_settings()
if settings.ENVIRONMENT.value != "testing":
    monitor = PerformanceMonitor.get_instance()
