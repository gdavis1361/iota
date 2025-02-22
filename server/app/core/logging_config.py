import json
import logging
import re
import sys
import threading
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import sqlalchemy


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    name: str
    type: MetricType
    description: str
    labels: List[str]
    domain: str


class DomainMetrics:
    """Domain-specific metric definitions"""

    # Frontend/UX Metrics
    FRONTEND = [
        MetricDefinition(
            "page_load_time",
            MetricType.HISTOGRAM,
            "Time to fully load page",
            ["route", "device_type"],
            "frontend",
        ),
        MetricDefinition(
            "dom_interactive_time",
            MetricType.HISTOGRAM,
            "Time until DOM is interactive",
            ["route"],
            "frontend",
        ),
        MetricDefinition(
            "first_paint_time", MetricType.HISTOGRAM, "Time to first paint", ["route"], "frontend"
        ),
        MetricDefinition(
            "js_errors",
            MetricType.COUNTER,
            "JavaScript error count",
            ["error_type", "component"],
            "frontend",
        ),
        MetricDefinition(
            "api_latency",
            MetricType.HISTOGRAM,
            "API call latency from client",
            ["endpoint"],
            "frontend",
        ),
    ]

    # Backend Service Metrics
    BACKEND = [
        MetricDefinition(
            "request_duration_seconds",
            MetricType.HISTOGRAM,
            "Request duration in seconds",
            ["endpoint", "method", "status"],
            "backend",
        ),
        MetricDefinition(
            "request_size_bytes",
            MetricType.HISTOGRAM,
            "Request size in bytes",
            ["endpoint"],
            "backend",
        ),
        MetricDefinition(
            "response_size_bytes",
            MetricType.HISTOGRAM,
            "Response size in bytes",
            ["endpoint"],
            "backend",
        ),
        MetricDefinition(
            "concurrent_requests",
            MetricType.GAUGE,
            "Number of concurrent requests",
            ["endpoint"],
            "backend",
        ),
        MetricDefinition(
            "middleware_duration_seconds",
            MetricType.HISTOGRAM,
            "Middleware processing time",
            ["middleware_name"],
            "backend",
        ),
    ]

    # Database Metrics
    DATABASE = [
        MetricDefinition(
            "query_duration_seconds",
            MetricType.HISTOGRAM,
            "Query execution time",
            ["query_type", "table"],
            "database",
        ),
        MetricDefinition(
            "connection_pool_size",
            MetricType.GAUGE,
            "Database connection pool size",
            ["pool_name"],
            "database",
        ),
        MetricDefinition(
            "connection_pool_utilization",
            MetricType.GAUGE,
            "Database connection pool utilization",
            ["pool_name"],
            "database",
        ),
        MetricDefinition(
            "deadlock_count",
            MetricType.COUNTER,
            "Number of deadlocks detected",
            ["table"],
            "database",
        ),
        MetricDefinition(
            "query_cache_hit_ratio", MetricType.GAUGE, "Query cache hit ratio", [], "database"
        ),
        MetricDefinition(
            "slow_query_count",
            MetricType.COUNTER,
            "Number of slow queries",
            ["query_type", "table"],
            "database",
        ),
        MetricDefinition(
            "transaction_rollbacks",
            MetricType.COUNTER,
            "Number of transaction rollbacks",
            ["cause"],
            "database",
        ),
    ]

    # Security Metrics
    SECURITY = [
        MetricDefinition(
            "auth_attempts",
            MetricType.COUNTER,
            "Authentication attempts",
            ["status", "method"],
            "security",
        ),
        MetricDefinition(
            "jwt_validation_errors",
            MetricType.COUNTER,
            "JWT validation errors",
            ["error_type"],
            "security",
        ),
        MetricDefinition(
            "rate_limit_hits",
            MetricType.COUNTER,
            "Rate limit threshold hits",
            ["endpoint", "ip_range"],
            "security",
        ),
        MetricDefinition(
            "suspicious_patterns",
            MetricType.COUNTER,
            "Suspicious access patterns",
            ["pattern_type"],
            "security",
        ),
        MetricDefinition(
            "privilege_escalations",
            MetricType.COUNTER,
            "Privilege escalation attempts",
            ["user_type"],
            "security",
        ),
    ]

    # Infrastructure Metrics
    INFRASTRUCTURE = [
        MetricDefinition(
            "cpu_usage_percent",
            MetricType.GAUGE,
            "CPU usage percentage",
            ["core"],
            "infrastructure",
        ),
        MetricDefinition(
            "memory_usage_bytes",
            MetricType.GAUGE,
            "Memory usage in bytes",
            ["type"],
            "infrastructure",
        ),
        MetricDefinition(
            "disk_io_bytes",
            MetricType.COUNTER,
            "Disk I/O in bytes",
            ["operation", "device"],
            "infrastructure",
        ),
        MetricDefinition(
            "network_io_bytes",
            MetricType.COUNTER,
            "Network I/O in bytes",
            ["interface", "direction"],
            "infrastructure",
        ),
        MetricDefinition(
            "file_descriptors",
            MetricType.GAUGE,
            "Open file descriptors",
            ["process_type"],
            "infrastructure",
        ),
    ]

    # Business Logic Metrics
    BUSINESS = [
        MetricDefinition(
            "feature_usage",
            MetricType.COUNTER,
            "Feature usage count",
            ["feature_name", "user_type"],
            "business",
        ),
        MetricDefinition(
            "error_count",
            MetricType.COUNTER,
            "Business logic errors",
            ["error_type", "component"],
            "business",
        ),
        MetricDefinition(
            "workflow_duration",
            MetricType.HISTOGRAM,
            "Workflow completion time",
            ["workflow_name"],
            "business",
        ),
        MetricDefinition(
            "conversion_rate",
            MetricType.GAUGE,
            "Feature conversion rate",
            ["feature_name"],
            "business",
        ),
    ]

    # ML Model Metrics
    ML = [
        MetricDefinition(
            "prediction_latency",
            MetricType.HISTOGRAM,
            "Model prediction latency",
            ["model_name", "version"],
            "ml",
        ),
        MetricDefinition(
            "prediction_accuracy",
            MetricType.GAUGE,
            "Model prediction accuracy",
            ["model_name", "version"],
            "ml",
        ),
        MetricDefinition(
            "feature_importance",
            MetricType.GAUGE,
            "Feature importance scores",
            ["feature_name", "model"],
            "ml",
        ),
        MetricDefinition(
            "model_drift", MetricType.GAUGE, "Model prediction drift", ["model_name"], "ml"
        ),
    ]

    @classmethod
    def all_metrics(cls) -> List[MetricDefinition]:
        """Get all metric definitions"""
        return (
            cls.FRONTEND
            + cls.BACKEND
            + cls.DATABASE
            + cls.SECURITY
            + cls.INFRASTRUCTURE
            + cls.BUSINESS
            + cls.ML
        )


class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(float))
        self.histograms = defaultdict(lambda: defaultdict(list))
        self.window_size = timedelta(minutes=5)
        self.last_reset = datetime.utcnow()
        self.metric_definitions = {metric.name: metric for metric in DomainMetrics.all_metrics()}

    def record(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value with optional labels"""
        current_time = datetime.utcnow()
        if current_time - self.last_reset > self.window_size:
            self.metrics = defaultdict(lambda: defaultdict(float))
            self.histograms = defaultdict(lambda: defaultdict(list))
            self.last_reset = current_time

        metric_def = self.metric_definitions.get(name)
        if not metric_def:
            return

        label_key = self._format_label_key(labels) if labels else ""

        if metric_def.type in (MetricType.COUNTER, MetricType.GAUGE):
            if metric_def.type == MetricType.COUNTER:
                self.metrics[name][label_key] += value
            else:
                self.metrics[name][label_key] = value
        elif metric_def.type in (MetricType.HISTOGRAM, MetricType.SUMMARY):
            self.histograms[name][label_key].append(value)

    def _format_label_key(self, labels: Dict[str, str]) -> str:
        """Format labels into a string key"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all current metrics"""
        result = {}

        # Process regular metrics
        for name, values in self.metrics.items():
            result[name] = dict(values)

        # Process histograms
        for name, histograms in self.histograms.items():
            result[name] = {}
            for label_key, values in histograms.items():
                if values:
                    result[name][label_key] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                        "max": max(values),
                        "min": min(values),
                    }

        return result


class AlertThreshold:
    def __init__(
        self,
        name: str,
        category: str,
        metric: str,
        threshold: float,
        window: timedelta,
        severity: str,
    ):
        self.name = name
        self.category = category
        self.metric = metric
        self.threshold = threshold
        self.window = window
        self.severity = severity
        self.last_alert = None
        self.alert_count = 0


class AlertManager:
    def __init__(self):
        self.thresholds = [
            # System Alerts
            AlertThreshold("high_cpu", "system", "cpu_usage", 80, timedelta(minutes=5), "critical"),
            AlertThreshold(
                "high_memory", "system", "memory_usage", 85, timedelta(minutes=5), "critical"
            ),
            AlertThreshold(
                "many_zombies", "processes", "zombie_processes", 5, timedelta(minutes=5), "warning"
            ),
            # API Alerts
            AlertThreshold(
                "high_error_rate", "api", "error_rates", 0.05, timedelta(minutes=5), "critical"
            ),
            AlertThreshold(
                "slow_response", "api", "response_times", 1.0, timedelta(minutes=5), "warning"
            ),
            # Security Alerts
            AlertThreshold(
                "auth_failures", "security", "failed_auth", 10, timedelta(minutes=5), "critical"
            ),
            AlertThreshold(
                "rate_limiting", "security", "rate_limited", 100, timedelta(minutes=5), "warning"
            ),
            # Database Alerts
            AlertThreshold("db_errors", "db", "query_errors", 5, timedelta(minutes=5), "critical"),
            AlertThreshold(
                "cache_miss_rate", "db", "cache_misses", 100, timedelta(minutes=5), "warning"
            ),
            AlertThreshold("deadlocks", "db", "deadlocks", 1, timedelta(minutes=5), "critical"),
        ]

        self.alert_history = []

    def check_thresholds(self, metrics: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        current_time = datetime.utcnow()
        alerts = []

        for threshold in self.thresholds:
            if threshold.category not in metrics:
                continue

            category_metrics = metrics[threshold.category]
            if threshold.metric not in category_metrics:
                continue

            value = category_metrics[threshold.metric]

            # Check if we should alert
            should_alert = value >= threshold.threshold

            # Ensure we don't alert too frequently
            if should_alert and (
                threshold.last_alert is None
                or current_time - threshold.last_alert >= threshold.window
            ):
                alert = {
                    "name": threshold.name,
                    "severity": threshold.severity,
                    "value": value,
                    "threshold": threshold.threshold,
                    "timestamp": current_time.isoformat(),
                }

                threshold.last_alert = current_time
                threshold.alert_count += 1

                self.alert_history.append(alert)
                alerts.append(alert)

        return alerts


class DiagnosticsFormatter(logging.Formatter):
    def format(self, record):
        record.timestamp = datetime.utcnow().isoformat()
        if not hasattr(record, "correlation_id"):
            record.correlation_id = threading.current_thread().name

        if isinstance(record.msg, dict):
            record.message = json.dumps(record.msg)
        else:
            record.message = str(record.msg)

        return super().format(record)


class DiagnosticsLogger:
    def __init__(self, app_name: str = "jsquared"):
        self.app_name = app_name
        self.log_dir = Path(__file__).parents[3] / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.metrics = MetricsCollector()
        self.alert_manager = AlertManager()

        # Configure root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.DEBUG)

        # Create formatters
        detailed_formatter = DiagnosticsFormatter(
            "%(timestamp)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(detailed_formatter)
        self.root_logger.addHandler(console_handler)

        # File handlers for different concerns
        handlers = {
            "api": self._create_handler("api.log", detailed_formatter),
            "auth": self._create_handler("auth.log", detailed_formatter),
            "db": self._create_handler("db.log", detailed_formatter),
            "perf": self._create_handler("performance.log", detailed_formatter),
            "security": self._create_handler("security.log", detailed_formatter),
        }

        # Create specialized loggers
        self.loggers = {
            name: self._create_logger(name, handler) for name, handler in handlers.items()
        }

        # Start monitoring threads
        self._start_system_monitoring()
        self._start_api_monitoring()
        self._start_security_monitoring()
        self._start_database_monitoring()
        self._start_alert_monitoring()

    def _create_handler(self, filename: str, formatter: logging.Formatter) -> RotatingFileHandler:
        handler = RotatingFileHandler(
            self.log_dir / filename, maxBytes=10485760, backupCount=5  # 10MB
        )
        handler.setFormatter(formatter)
        return handler

    def _create_logger(self, name: str, handler: logging.Handler) -> logging.Logger:
        logger = logging.getLogger(f"{self.app_name}.{name}")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        return logger

    def _start_system_monitoring(self):
        def monitor():
            while True:
                try:
                    process = psutil.Process()
                    with process.oneshot():
                        # System Resources
                        self.metrics.record("cpu_usage_percent", process.cpu_percent())
                        self.metrics.record("memory_usage_bytes", process.memory_info().rss)
                        self.metrics.record("open_files", len(process.open_files()))
                        self.metrics.record("thread_count", process.num_threads())

                        # Process Management
                        python_processes = [
                            p for p in psutil.process_iter() if "python" in p.name().lower()
                        ]
                        self.metrics.record("total_python_processes", len(python_processes))
                        self.metrics.record(
                            "zombie_processes",
                            len([p for p in python_processes if p.status() == "zombie"]),
                        )

                        # Log system metrics
                        self.loggers["perf"].info(
                            {
                                "event": "system_metrics",
                                "metrics": self.metrics.get_metrics(),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                except Exception as e:
                    self.loggers["perf"].error(f"System monitoring error: {str(e)}")
                time.sleep(10)

        threading.Thread(target=monitor, daemon=True).start()

    def _start_api_monitoring(self):
        def monitor():
            while True:
                try:
                    metrics = self.metrics.get_metrics()
                    api_metrics = {
                        "response_times": metrics.get("api", {}).get("response_times", 0),
                        "error_rates": metrics.get("api", {}).get("error_rates", 0),
                        "requests_per_minute": metrics.get("api", {}).get("requests", 0),
                        "endpoint_usage": metrics.get("api", {}).get("endpoint_hits", {}),
                    }

                    self.loggers["api"].info(
                        {
                            "event": "api_metrics",
                            "metrics": api_metrics,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as e:
                    self.loggers["api"].error(f"API monitoring error: {str(e)}")
                time.sleep(60)

        threading.Thread(target=monitor, daemon=True).start()

    def _start_security_monitoring(self):
        def monitor():
            while True:
                try:
                    metrics = self.metrics.get_metrics()
                    security_metrics = {
                        "failed_auth_attempts": metrics.get("security", {}).get("failed_auth", 0),
                        "suspicious_requests": metrics.get("security", {}).get("suspicious", 0),
                        "rate_limited_ips": metrics.get("security", {}).get("rate_limited", 0),
                        "jwt_validation_failures": metrics.get("security", {}).get(
                            "jwt_failures", 0
                        ),
                    }

                    self.loggers["security"].info(
                        {
                            "event": "security_metrics",
                            "metrics": security_metrics,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as e:
                    self.loggers["security"].error(f"Security monitoring error: {str(e)}")
                time.sleep(60)

        threading.Thread(target=monitor, daemon=True).start()

    def _start_database_monitoring(self):
        def monitor():
            while True:
                try:
                    metrics = self.metrics.get_metrics()
                    db_metrics = {
                        "active_connections": metrics.get("db", {}).get("active_connections", 0),
                        "query_times": metrics.get("db", {}).get("query_times", {}),
                        "deadlocks": metrics.get("db", {}).get("deadlocks", 0),
                        "cache_hits": metrics.get("db", {}).get("cache_hits", 0),
                        "cache_misses": metrics.get("db", {}).get("cache_misses", 0),
                    }

                    self.loggers["db"].info(
                        {
                            "event": "database_metrics",
                            "metrics": db_metrics,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as e:
                    self.loggers["db"].error(f"Database monitoring error: {str(e)}")
                time.sleep(30)

        threading.Thread(target=monitor, daemon=True).start()

    def _start_alert_monitoring(self):
        def monitor():
            while True:
                try:
                    metrics = self.metrics.get_metrics()
                    alerts = self.alert_manager.check_thresholds(metrics)

                    for alert in alerts:
                        self.loggers["perf"].warning({"event": "alert_triggered", "alert": alert})

                        # Log critical alerts to security logger as well
                        if alert["severity"] == "critical":
                            self.loggers["security"].warning(
                                {"event": "critical_alert", "alert": alert}
                            )
                except Exception as e:
                    self.loggers["perf"].error(f"Alert monitoring error: {str(e)}")
                time.sleep(10)

        threading.Thread(target=monitor, daemon=True).start()

    @contextmanager
    def track_request(self, endpoint: str, method: str, labels: Dict[str, str] = None):
        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time

            # Record basic request metrics
            self.metrics.record(
                "request_duration_seconds",
                duration,
                {"endpoint": endpoint, "method": method, **(labels or {})},
            )

            # Track concurrent requests
            self.metrics.record("concurrent_requests", 1, {"endpoint": endpoint})

        except Exception as e:
            self.metrics.record(
                "error_count", 1, {"error_type": type(e).__name__, "component": "api"}
            )
            raise
        finally:
            # Decrease concurrent request count
            self.metrics.record("concurrent_requests", -1, {"endpoint": endpoint})

    @contextmanager
    def track_query(self, query_type: str, table: str):
        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time

            self.metrics.record(
                "query_duration_seconds", duration, {"query_type": query_type, "table": table}
            )

            if duration > 1.0:  # Slow query threshold
                self.metrics.record(
                    "slow_query_count", 1, {"query_type": query_type, "table": table}
                )

        except Exception as e:
            self.metrics.record("transaction_rollbacks", 1, {"cause": type(e).__name__})
            raise

    def track_ml_prediction(
        self, model_name: str, version: str, latency: float, accuracy: Optional[float] = None
    ):
        """Track ML model predictions"""
        self.metrics.record(
            "prediction_latency", latency, {"model_name": model_name, "version": version}
        )

        if accuracy is not None:
            self.metrics.record(
                "prediction_accuracy", accuracy, {"model_name": model_name, "version": version}
            )

    def track_feature_usage(self, feature_name: str, user_type: str):
        """Track business feature usage"""
        self.metrics.record(
            "feature_usage", 1, {"feature_name": feature_name, "user_type": user_type}
        )

    def track_frontend_timing(
        self, route: str, timing_type: str, duration: float, device_type: str = "unknown"
    ):
        """Track frontend performance metrics"""
        self.metrics.record(
            f"{timing_type}_time", duration, {"route": route, "device_type": device_type}
        )


diagnostics = DiagnosticsLogger()


def setup_logging(log_level: str = "DEBUG"):
    """Initialize the logging system."""
    return diagnostics
