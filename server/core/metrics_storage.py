"""Persistent storage for performance metrics."""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Union


class MetricsStorage:
    """Store and retrieve performance metrics."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize metrics storage."""
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "metrics.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    duration REAL NOT NULL,
                    error BOOLEAN NOT NULL,
                    is_slow BOOLEAN NOT NULL
                )
            """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_operation ON metrics(operation)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)")

        self._lock = threading.Lock()

    def insert_metric(
        self, operation: str, duration: float, error: bool = False, is_slow: bool = False
    ) -> None:
        """Insert a new metric."""
        timestamp = int(time.time())
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO metrics (operation, timestamp, duration, error, is_slow) "
                "VALUES (?, ?, ?, ?, ?)",
                (operation, timestamp, duration, error, is_slow),
            )

    def get_metrics(self, operation: str) -> List[Dict]:
        """Get all metrics for an operation."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM metrics WHERE operation = ? ORDER BY timestamp DESC", (operation,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_metrics_in_window(self, operation: str, window_seconds: int) -> List[Dict]:
        """Get metrics within a time window."""
        cutoff = int(time.time()) - window_seconds
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM metrics WHERE operation = ? AND timestamp >= ? "
                "ORDER BY timestamp DESC",
                (operation, cutoff),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_aggregated_stats(self, operation: str, window_seconds: Optional[int] = None) -> Dict:
        """Get aggregated statistics for an operation."""
        query = """
            SELECT
                COUNT(*) as total_count,
                SUM(CASE WHEN error THEN 1 ELSE 0 END) as error_count,
                CAST(SUM(CASE WHEN error THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as error_rate,
                AVG(duration) as avg_duration,
                MIN(duration) as min_duration,
                MAX(duration) as max_duration,
                SUM(CASE WHEN is_slow THEN 1 ELSE 0 END) as slow_count
            FROM metrics
            WHERE operation = ?
        """
        params = [operation]

        if window_seconds is not None:
            query += " AND timestamp >= ?"
            params.append(int(time.time()) - window_seconds)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return dict(cursor.fetchone())

    def cleanup_old_metrics(self, window_seconds: int) -> None:
        """Delete metrics older than the window."""
        cutoff = int(time.time()) - window_seconds
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
