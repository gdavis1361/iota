"""Tests for metrics storage."""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from server.core.metrics_storage import MetricsStorage


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_metrics.db"


@pytest.fixture
def storage(temp_db_path):
    """Create a test metrics storage instance."""
    return MetricsStorage(temp_db_path)


def test_init_db(storage, temp_db_path):
    """Test database initialization."""
    assert temp_db_path.exists()

    # Check schema
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='metrics'
        """
        )
        assert cursor.fetchone() is not None


def test_record_metric(storage):
    """Test recording a single metric."""
    storage.record_metric(category="test", operation="op1", duration_ms=100.0, had_error=False)

    metrics = storage.get_metrics(category="test", operation="op1")
    assert len(metrics) == 1
    assert metrics[0]["category"] == "test"
    assert metrics[0]["operation"] == "op1"
    assert metrics[0]["duration_ms"] == 100.0
    assert not metrics[0]["had_error"]


def test_get_metrics_filtering(storage):
    """Test filtering metrics."""
    # Add test data
    now = datetime.utcnow()
    earlier = now - timedelta(hours=1)

    storage.record_metric("cat1", "op1", 100.0, False)
    storage.record_metric("cat1", "op2", 200.0, True)
    storage.record_metric("cat2", "op1", 300.0, False)

    # Test category filter
    cat1_metrics = storage.get_metrics(category="cat1")
    assert len(cat1_metrics) == 2

    # Test operation filter
    op1_metrics = storage.get_metrics(operation="op1")
    assert len(op1_metrics) == 2

    # Test combined filters
    specific_metrics = storage.get_metrics(category="cat1", operation="op1")
    assert len(specific_metrics) == 1


def test_get_summary(storage):
    """Test getting metric summaries."""
    # Add test data
    storage.record_metric("test", "op1", 100.0, False)
    storage.record_metric("test", "op1", 200.0, True)
    storage.record_metric("test", "op1", 300.0, False)

    summary = storage.get_summary(category="test", operation="op1")
    assert "test" in summary
    assert "op1" in summary["test"]

    op_summary = summary["test"]["op1"]
    assert op_summary["count"] == 3
    assert op_summary["errors"] == 1
    assert op_summary["avg_duration"] == 200.0
    assert op_summary["min_duration"] == 100.0
    assert op_summary["max_duration"] == 300.0


def test_concurrent_access(storage):
    """Test concurrent access to metrics storage."""
    import threading

    def record_metrics():
        for i in range(100):
            storage.record_metric(
                category="concurrent",
                operation=f"op{i % 2}",
                duration_ms=float(i),
                had_error=i % 5 == 0,
            )

    # Create multiple threads to record metrics
    threads = [threading.Thread(target=record_metrics) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Verify results
    metrics = storage.get_metrics(category="concurrent")
    assert len(metrics) == 500  # 5 threads * 100 records

    summary = storage.get_summary(category="concurrent")
    assert summary["concurrent"]["op0"]["count"] == 250
    assert summary["concurrent"]["op1"]["count"] == 250
