# Error Logger

## Overview

The error logger provides structured logging with comprehensive error tracking and correlation. It uses `structlog` for consistent log formatting and supports different logging levels based on the environment.

## Features

1. **Structured Logging**
   - JSON-formatted logs
   - Consistent field names
   - Correlation IDs
   - Context preservation

2. **Environment-Aware**
   - Development: Human-readable format
   - Production: JSON format
   - Testing: Captured for verification

3. **Performance Tracking**
   - Operation duration
   - Error categorization
   - Stack trace preservation
   - Context capture

## Implementation

### Logger Configuration

```python
import structlog
from typing import Any, Dict

def configure_logging(environment: str) -> None:
    """Configure structured logging based on environment."""
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if environment == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### Error Context

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ErrorContext:
    """Error context container."""

    operation: str
    error_type: str
    message: str
    correlation_id: str
    duration_ms: float
    stack_trace: Optional[str] = None
    additional_info: Dict[str, Any] = None
```

### Logger Implementation

```python
import structlog
from typing import Optional

logger = structlog.get_logger()

class ErrorLogger:
    """Structured error logger with context tracking."""

    def __init__(self):
        """Initialize with structured logger."""
        self.logger = structlog.get_logger()

    def log_error(
        self,
        operation: str,
        error: Exception,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log error with context."""
        context = ErrorContext(
            operation=operation,
            error_type=type(error).__name__,
            message=str(error),
            correlation_id=correlation_id or "unknown",
            duration_ms=kwargs.get("duration_ms", 0),
            stack_trace=self._format_stack_trace(error),
            additional_info=kwargs
        )

        self.logger.error(
            "operation_error",
            operation=context.operation,
            error_type=context.error_type,
            message=context.message,
            correlation_id=context.correlation_id,
            duration_ms=context.duration_ms,
            stack_trace=context.stack_trace,
            **context.additional_info
        )
```

## Usage Examples

### Basic Error Logging

```python
from server.core.logging import ErrorLogger

logger = ErrorLogger()

try:
    perform_operation()
except Exception as e:
    logger.log_error(
        operation="perform_operation",
        error=e,
        correlation_id="123",
        user_id="user_123"
    )
```

### With Performance Monitoring

```python
from server.core.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
logger = ErrorLogger()

try:
    with monitor.monitor("critical_operation") as op:
        perform_critical_operation()
except Exception as e:
    logger.log_error(
        operation="critical_operation",
        error=e,
        duration_ms=op.duration,
        is_slow=op.is_slow
    )
```

### Testing Error Logging

```python
def test_error_logging():
    """Test error logger functionality."""
    logger = ErrorLogger()

    try:
        raise ValueError("test error")
    except Exception as e:
        logger.log_error(
            operation="test_operation",
            error=e,
            correlation_id="test_123"
        )

    # Verify log output
    log_entry = get_last_log_entry()
    assert log_entry["operation"] == "test_operation"
    assert log_entry["error_type"] == "ValueError"
    assert "test error" in log_entry["message"]
```

## Log Levels

### ERROR
- Unhandled exceptions
- Configuration failures
- Data corruption
- Security violations

### WARNING
- Performance degradation
- Resource warnings
- Deprecated feature usage
- Non-critical failures

### INFO
- Operation completion
- State changes
- Configuration updates
- Service status

### DEBUG
- Detailed operation steps
- Variable states
- Function entry/exit
- Performance metrics

## Best Practices

1. **Error Context**
   - Always include operation name
   - Add correlation IDs
   - Preserve stack traces
   - Include relevant context

2. **Performance Impact**
   - Use sampling for high-volume errors
   - Batch similar errors
   - Limit stack trace depth
   - Control log volume

3. **Security**
   - Sanitize sensitive data
   - Mask credentials
   - Control log access
   - Rotate log files

## References

- [Performance Monitor](/Users/allan/Projects/iota/docs/perf_monitor.md)
- [Configuration Parser](/Users/allan/Projects/iota/docs/config_parser.md)
- [Architecture Overview](/Users/allan/Projects/iota/docs/architecture.md)
