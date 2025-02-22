# ADR 0001: Configuration Management Overhaul

## Status
Accepted

## Context
The project needed to migrate to Pydantic v2 while improving configuration management, particularly around testing. Key challenges included:
- Global state causing test interference
- Difficulty in mocking configuration for tests
- Inconsistent environment variable handling
- Need for better type safety and validation

## Decision
We decided to:
1. Remove global settings instances
2. Create dedicated factory functions for settings creation
3. Implement test-specific configuration helpers
4. Add proper validation using Pydantic v2 models
5. Consolidate all configuration code into a single module to avoid duplication

### Key Components
- `Settings` class using `pydantic_settings.BaseSettings`
- `create_settings()` factory function for production use
- `create_test_settings()` helper for test environment
- Endpoint-specific rate limit configuration

### Configuration Pattern
```python
# Production usage
settings = create_settings()

# Test usage
test_settings = create_test_settings()
```

## Consequences

### Positive
- Better test isolation
- Type-safe configuration
- Clearer initialization patterns
- Improved error messages
- More maintainable codebase
- Reduced code duplication

### Negative
- Breaking change for direct settings access
- Need to update existing tests
- Additional boilerplate in test setup
- Additional setup required for development
- Need to maintain comprehensive validation rules
- Potential for increased startup time due to validation

## Implementation Notes

### Environment Variables
Required environment variables:
- `ENVIRONMENT`: Application environment (development, testing, staging, production)
- `SECRET_KEY`: Application secret key (min 32 chars)
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_DB`: Database name

### Rate Limiting Configuration
Rate limits are now configured using Pydantic models:
```python
RateLimitConfig(
    default_window=60,
    default_max_requests=100,
    endpoint_limits={
        "/api/endpoint": EndpointLimit(
            window=30,
            max_requests=50
        )
    }
)
```

### Testing
Test configuration provides sensible defaults:
```python
test_settings = create_test_settings()
assert test_settings.ENVIRONMENT == EnvironmentType.TESTING
assert test_settings.DEBUG is True
```

## Module Structure
```
server/core/config/
├── __init__.py
├── base.py         # Base configuration class
├── schema.py       # Pydantic models for config validation
└── validators.py   # Custom validation functions
```

## Migration Guide

### Step 1: Update Imports
```python
# Old
from server.core.config import settings

# New
from server.core.config import create_settings
settings = create_settings()
```

### Step 2: Update Tests
```python
# Old
from server.core.config import settings

# New
@pytest.fixture
def test_settings():
    return create_test_settings()
```

### Step 3: Update Rate Limit Usage
```python
# Old
rate_limit = {
    "window": 60,
    "max_requests": 100
}

# New
rate_limit = EndpointLimit(
    window=60,
    max_requests=100
)
```

## References
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Python Testing Best Practices](https://docs.pytest.org/en/stable/explanation/good-practices.html)
For more information, see:
- [Contributing Guidelines](/Users/allan/Projects/iota/docs/adr/../contributing.md)
- [Pre-commit Setup](/Users/allan/Projects/iota/docs/adr/../pre-commit.md)
- [Development Guide](/Users/allan/Projects/iota/docs/adr/../development.md)
