# ADR 0002: Performance Monitoring System

## Status
Accepted

## Context
The infrastructure management tools require comprehensive performance tracking and metrics storage to:
- Monitor operation durations and identify slow operations
- Track error rates and patterns
- Provide insights for optimization
- Enable data-driven decision making

## Decision
We implemented a monitoring system with the following key components:

1. **PerformanceMonitor with Context Manager**
   - Uses `time.perf_counter_ns()` for nanosecond precision
   - Implements Python context manager pattern for clean operation tracking
   - Automatically detects and flags slow operations

2. **SQLite-based Metrics Storage**
   - Persistent storage with minimal overhead
   - Thread-safe operations
   - Schema includes operation name, timestamp, duration, error flag, and slow operation flag

3. **Thread-Safe Implementation**
   - Singleton pattern with proper locking
   - Safe concurrent metric updates
   - Transaction-based database operations

## Consequences

### Positive
- High-precision timing for accurate measurements
- Clean, Pythonic API through context manager
- Minimal performance overhead (~1-2ms per operation)
- No external dependencies for basic functionality
- Comprehensive test coverage

### Negative
- Local SQLite storage may need periodic cleanup
- Limited to single-machine metrics (no distributed tracking)
- Basic visualization capabilities without external tools

## Implementation Notes

### Usage Example
```python
from server.core.monitoring import PerformanceMonitor

with PerformanceMonitor().monitor("operation_name"):
    # Operation code here
    perform_task()
```

### Key Metrics
- Operation duration (nanosecond precision)
- Error occurrence
- Slow operation detection (configurable threshold)
- Aggregated statistics (count, error rate, avg/min/max duration)

### Configuration
```python
SLOW_REQUEST_THRESHOLD_MS = 1000  # Mark operations over 1 second as slow
SAMPLING_WINDOW_SECONDS = 3600    # Keep last hour of metrics
ERROR_RATE_THRESHOLD = 0.1        # Alert if error rate exceeds 10%
```

## Future Considerations
1. Implement metric rotation/cleanup mechanism
2. Add Grafana/Prometheus integration
3. Consider distributed metrics collection
4. Implement automated alerting system
