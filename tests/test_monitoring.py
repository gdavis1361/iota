"""Test suite for the monitoring system."""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Generator

import pytest
from pytest import MonkeyPatch

from server.core.metrics_storage import MetricsStorage
from server.core.monitoring import PerformanceMonitor


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_metrics.db"


@pytest.fixture
def metrics_storage(temp_db_path: Path) -> Generator[MetricsStorage, None, None]:
    """Create a test metrics storage instance."""
    storage = MetricsStorage(str(temp_db_path))
    yield storage
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def performance_monitor(metrics_storage: MetricsStorage) -> PerformanceMonitor:
    """Create a test performance monitor instance."""
    return PerformanceMonitor(metrics_storage)


def test_metric_insertion(metrics_storage: MetricsStorage):
    """Test basic metric insertion and retrieval."""
    # Insert test metrics
    metrics_storage.insert_metric("version_bump", duration=100, error=False)
    metrics_storage.insert_metric("version_bump", duration=200, error=True)

    # Retrieve and verify metrics
    metrics = metrics_storage.get_metrics("version_bump")
    assert len(metrics) == 2
    assert sum(1 for m in metrics if m["error"]) == 1
    assert sum(m["duration"] for m in metrics) == 300


def test_thread_safety(metrics_storage: MetricsStorage):
    """Test thread-safe metric operations."""

    def insert_metrics():
        for _ in range(100):
            metrics_storage.insert_metric("concurrent_test", duration=50, error=False)

    threads = [threading.Thread(target=insert_metrics) for _ in range(5)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    metrics = metrics_storage.get_metrics("concurrent_test")
    assert len(metrics) == 500  # 5 threads * 100 inserts


def test_performance_monitor_context(performance_monitor: PerformanceMonitor):
    """Test the performance monitor context manager."""
    with performance_monitor.monitor("test_operation"):
        time.sleep(0.1)  # Simulate work

    metrics = performance_monitor.storage.get_metrics("test_operation")
    assert len(metrics) == 1
    assert metrics[0]["duration"] >= 100  # At least 100ms
    assert not metrics[0]["error"]


def test_error_handling(performance_monitor: PerformanceMonitor):
    """Test error handling in performance monitoring."""
    with pytest.raises(ValueError):
        with performance_monitor.monitor("error_test"):
            raise ValueError("Test error")

    metrics = performance_monitor.storage.get_metrics("error_test")
    assert len(metrics) == 1
    assert metrics[0]["error"]


def test_metric_cleanup(metrics_storage: MetricsStorage):
    """Test metric cleanup functionality."""
    # Insert old metrics
    old_time = int(time.time()) - 7200  # 2 hours ago
    with sqlite3.connect(metrics_storage.db_path) as conn:
        conn.execute(
            "INSERT INTO metrics (operation, timestamp, duration, error, is_slow) "
            "VALUES (?, ?, ?, ?, ?)",
            ("old_metric", old_time, 100, 0, 0),
        )

    # Insert recent metrics
    metrics_storage.insert_metric("recent_metric", duration=100, error=False)

    # Clean up old metrics
    metrics_storage.cleanup_old_metrics(3600)  # 1 hour window

    # Verify cleanup
    old_metrics = metrics_storage.get_metrics("old_metric")
    recent_metrics = metrics_storage.get_metrics("recent_metric")
    assert len(old_metrics) == 0
    assert len(recent_metrics) == 1


def test_metric_aggregation(metrics_storage: MetricsStorage):
    """Test metric aggregation functionality."""
    # Insert test data
    for i in range(10):
        metrics_storage.insert_metric(
            "aggregation_test",
            duration=100 * (i + 1),
            error=i >= 8,  # Make last 2 operations errors
        )

    # Get aggregated metrics
    stats = metrics_storage.get_aggregated_stats("aggregation_test")

    assert stats["total_count"] == 10
    assert stats["error_count"] == 2
    assert stats["error_rate"] == 0.2
    assert 500 <= stats["avg_duration"] <= 600  # Average should be around 550ms
    assert stats["min_duration"] == 100
    assert stats["max_duration"] == 1000


def test_slow_operation_tracking(performance_monitor: PerformanceMonitor):
    """Test slow operation detection."""
    # Configure slow threshold
    performance_monitor.slow_threshold_ms = 50

    # Test fast operation
    with performance_monitor.monitor("fast_op"):
        time.sleep(0.01)  # 10ms

    # Test slow operation
    with performance_monitor.monitor("slow_op"):
        time.sleep(0.1)  # 100ms

    fast_metrics = performance_monitor.storage.get_metrics("fast_op")
    slow_metrics = performance_monitor.storage.get_metrics("slow_op")

    assert not fast_metrics[0]["is_slow"]
    assert slow_metrics[0]["is_slow"]


def test_sampling_window(metrics_storage: MetricsStorage):
    """Test metric sampling window functionality."""
    # Insert metrics at different times
    current_time = int(time.time())

    # Insert old metrics (outside window)
    with sqlite3.connect(metrics_storage.db_path) as conn:
        conn.execute(
            "INSERT INTO metrics (operation, timestamp, duration, error, is_slow) "
            "VALUES (?, ?, ?, ?, ?)",
            ("window_test", current_time - 7200, 100, 0, 0),  # 2 hours ago
        )

    # Insert recent metrics
    metrics_storage.insert_metric("window_test", duration=200, error=False)

    # Get metrics within 1-hour window
    recent_metrics = metrics_storage.get_metrics_in_window("window_test", window_seconds=3600)

    assert len(recent_metrics) == 1
    assert recent_metrics[0]["duration"] == 200
