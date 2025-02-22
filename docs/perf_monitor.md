# Performance Monitor

## Overview

The Performance Monitor provides high-precision timing and metric collection for critical operations. It uses a context manager pattern for clean operation tracking and maintains thread-safe metric storage.

## Features

1. **High-Precision Timing**
   - Nanosecond accuracy using `time.perf_counter_ns()`
   - Consistent timing across platforms
   - Low overhead measurement

2. **Context Manager Interface**
   - Clean operation wrapping
   - Automatic error tracking
   - Duration calculation
   - Slow operation detection

3. **Thread-Safe Storage**
   - SQLite-based persistence
   - Concurrent operation support
   - Atomic updates
   - Data integrity protection

## Implementation

### Performance Monitor

```python
import contextlib
import threading
import time
from typing import Optional

class PerformanceMonitor:
    """Monitor performance of critical operations."""

    def __init__(self, storage: Optional[MetricsStorage] = None):
        """Initialize the monitor."""
        self.storage = storage or MetricsStorage()
        self.slow_threshold_ms = 1000  # 1 second
        self._lock = threading.Lock()

    @contextlib.contextmanager
    def monitor(self, operation: str):
        """Monitor an operation's performance."""
        start_time = time.perf_counter_ns()
        error = False
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            duration = (time.perf_counter_ns() - start_time) / 1_000_000
            self.storage.insert_metric(
                operation,
                duration=duration,
                error=error,
                is_slow=duration > self.slow_threshold_ms
            )
```

### Metrics Storage

```python
import sqlite3
import threading
from typing import Dict, List

class MetricsStorage:
    """Thread-safe storage for performance metrics."""

    def __init__(self, db_path: str = "metrics.db"):
        """Initialize storage with database path."""
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def insert_metric(
        self,
        operation: str,
        duration: float,
        error: bool = False,
        is_slow: bool = False
    ) -> None:
        """Insert a performance metric."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO metrics
                    (operation, timestamp, duration, error, is_slow)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (operation, time.time(), duration, error, is_slow)
                )
```

## Usage Examples

### Basic Operation Monitoring

```python
from server.core.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()

# Monitor an operation
with monitor.monitor("process_data"):
    process_large_dataset()

# Get metrics
metrics = monitor.storage.get_metrics("process_data")
print(f"Average duration: {sum(m['duration'] for m in metrics) / len(metrics)}ms")
```

### Error Handling

```python
try:
    with monitor.monitor("risky_operation"):
        perform_risky_operation()
except Exception as e:
    # Error automatically tracked in metrics
    handle_error(e)
```

### Slow Operation Detection

```python
# Configure slow threshold
monitor.slow_threshold_ms = 500  # 500ms

with monitor.monitor("api_call"):
    response = make_api_call()

# Check recent slow operations
slow_ops = monitor.storage.get_metrics_in_window(
    "api_call",
    window_seconds=3600,
    filter_slow=True
)
```

## Configuration

### Settings

```python
# In server/core/config/base.py
SLOW_REQUEST_THRESHOLD_MS = 1000  # Mark operations over 1 second as slow
SAMPLING_WINDOW_SECONDS = 3600    # Keep last hour of metrics
ERROR_RATE_THRESHOLD = 0.1        # Alert if error rate exceeds 10%
```

### Environment Variables

```bash
# Optional overrides
SLOW_REQUEST_THRESHOLD_MS=500
SAMPLING_WINDOW_SECONDS=7200
ERROR_RATE_THRESHOLD=0.05
```

## Metric Types

### Duration Metrics
- Operation duration in milliseconds
- Slow operation flag
- Timestamp
- Operation name

### Error Metrics
- Error occurrence flag
- Error type (if applicable)
- Stack trace (if available)
- Context data

### Aggregated Stats
- Total count
- Error count
- Error rate
- Average duration
- Min/Max duration
- Slow operation count

## Best Practices

1. **Operation Monitoring**
   - Monitor critical operations
   - Set appropriate thresholds
   - Track error contexts
   - Clean up old metrics

2. **Performance Impact**
   - Use sampling for high-frequency operations
   - Clean up old metrics regularly
   - Monitor storage growth
   - Optimize queries

3. **Error Handling**
   - Always use context manager
   - Capture error context
   - Track error patterns
   - Set up alerts

## Testing

### Unit Tests

```python
def test_performance_monitor():
    """Test performance monitoring."""
    monitor = PerformanceMonitor()

    with monitor.monitor("test_op"):
        time.sleep(0.1)  # 100ms operation

    metrics = monitor.storage.get_metrics("test_op")
    assert len(metrics) == 1
    assert 90 <= metrics[0]["duration"] <= 110
    assert not metrics[0]["error"]
```

### Integration Tests

```python
def test_concurrent_monitoring():
    """Test concurrent operation monitoring."""
    monitor = PerformanceMonitor()

    def monitored_operation():
        with monitor.monitor("concurrent_op"):
            time.sleep(0.01)

    threads = [
        threading.Thread(target=monitored_operation)
        for _ in range(10)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    metrics = monitor.storage.get_metrics("concurrent_op")
    assert len(metrics) == 10
```

## References

- [Error Logger](/Users/allan/Projects/iota/docs/error_logger.md)
- [Configuration Parser](/Users/allan/Projects/iota/docs/config_parser.md)
- [Architecture Overview](/Users/allan/Projects/iota/docs/architecture.md)
- [Monitoring System ADR](/Users/allan/Projects/iota/docs/adr/0002-monitoring-system.md)
