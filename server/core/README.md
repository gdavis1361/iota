# Iota Configuration System

## Overview
The Iota configuration system provides robust, type-safe configuration management using Pydantic v2. It supports environment-specific validation rules, secure defaults, and comprehensive error reporting.

## Configuration Variables

### Core Settings
```env
# Required Settings
SECRET_KEY=your-secret-key  # Min 32 characters
APP_NAME=iota              # Default: "iota"

# Optional Settings
ENVIRONMENT=development    # Options: development, staging, production, test
DEBUG=false               # Default: false
LOG_LEVEL=INFO           # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json          # Options: json, console
ALLOWED_HOSTS=*          # Comma-separated list. '*' not allowed in production
VERSION=2.0              # Must match supported schema version
```

### Sentry Settings
```env
SENTRY_ENABLED=false                # Enable/disable Sentry integration
SENTRY_DSN=                         # Required if Sentry enabled
SENTRY_ENVIRONMENT=development      # Override environment for Sentry
SENTRY_TRACES_SAMPLE_RATE=0.1      # Range: 0.0 to 1.0
SENTRY_PROFILES_SAMPLE_RATE=0.1    # Range: 0.0 to 1.0
```

### Performance Settings
```env
SLOW_REQUEST_THRESHOLD_MS=1000.0    # Must be positive
ERROR_RATE_THRESHOLD=0.1           # Range: 0.0 to 1.0
SLOW_RATE_THRESHOLD=0.1           # Range: 0.0 to 1.0
```

## Environment-Specific Validation

### Production Environment
- Wildcard (*) not allowed in ALLOWED_HOSTS
- SECRET_KEY must be at least 32 characters
- Sentry DSN required if Sentry is enabled

### Test Environment
- Sets APP_NAME to "test-app"
- Enables DEBUG mode
- Disables Sentry by default
- Sets maximum sampling rates for traces and profiles

## Validation Rules

### Security Rules
1. SECRET_KEY:
   - Minimum length: 32 characters
   - Must be provided (no default)

2. ALLOWED_HOSTS:
   - Production: No wildcard (*) allowed
   - Other environments: Wildcard allowed
   - Default: ["*"]

3. Sentry Configuration:
   - DSN Format: https://<key>@<host>/<project-id>
   - Required if Sentry enabled
   - Environment-specific settings

### Rate Values
All rate values must be between 0 and 1:
- SENTRY_TRACES_SAMPLE_RATE
- SENTRY_PROFILES_SAMPLE_RATE
- ERROR_RATE_THRESHOLD
- SLOW_RATE_THRESHOLD

### Log Settings
1. LOG_LEVEL:
   - Valid options: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - Case-insensitive input, stored as uppercase

2. LOG_FORMAT:
   - Valid options: json, console
   - Case-insensitive input, stored as lowercase

### Version Management
- Current Schema Version: `V2.0`
- Supported Configuration Versions: `V1.0`, `V2.0`

## Error Messages
The configuration system provides detailed error messages for validation failures:

```python
# Invalid SECRET_KEY
ValueError: SECRET_KEY must be at least 32 characters long

# Invalid environment
ValueError: Invalid environment 'invalid'. Must be one of development, staging, production, test

# Invalid ALLOWED_HOSTS in production
ValueError: Wildcard (*) not allowed in ALLOWED_HOSTS in production environment

# Invalid rate value
ValueError: Rate value must be between 0 and 1

# Invalid log level
ValueError: Invalid log level. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL

# Version mismatch
ValueError: Configuration version '1.0' does not match supported schema version 'V2.0'
```

## Usage Examples

### Basic Usage
```python
from server.core.config import Settings

# Load configuration from environment variables
settings = Settings()

# Access configuration values
debug_mode = settings.DEBUG
app_name = settings.APP_NAME
```

### Test Environment
```python
# Test settings with minimum configuration
settings = Settings(
    ENVIRONMENT="test",
    SECRET_KEY="x" * 32
)

# All test defaults are automatically applied
assert settings.APP_NAME == "test-app"
assert settings.DEBUG == True
assert settings.SENTRY_ENABLED == False
```

### Production Environment
```python
# Production settings require specific hosts
settings = Settings(
    ENVIRONMENT="production",
    SECRET_KEY="your-secure-secret-key-min-32-chars",
    ALLOWED_HOSTS=["api.example.com", "web.example.com"]
)
```

## Migration from v1 to v2
If you're upgrading from an older version, note these changes:

1. Validator Syntax:
   - Old: `@validator`
   - New: `@field_validator`

2. Pre-validation:
   - Old: Multiple `@validator(..., pre=True)`
   - New: Single `@model_validator(mode='before')`

3. Configuration:
   - Old: `class Config`
   - New: `model_config = SettingsConfigDict`

## Best Practices
1. Always use environment variables for sensitive values
2. Set strict production configurations
3. Use test environment for automated testing
4. Monitor validation errors in logs
5. Keep configuration documentation updated

## Testing
Run configuration tests with:
```bash
python -m pytest tests/core/test_validate_config.py -v
```

## Version Compatibility Matrix

| Config Version | Schema Version | Status | Migration Path |
|---------------|----------------|--------|----------------|
| V1.0          | V2.0          | Legacy | Manual upgrade required |
| V2.0          | V2.0          | Current | N/A |

#### Migration Guidelines

When upgrading from V1.0 to V2.0:
1. Review your configuration file
2. Update the VERSION field to "2.0"
3. Add any new required fields
4. Remove deprecated fields
5. Validate using the configuration test suite

## Health Checks

The configuration system provides health checks that include version status:

```python
health = config_monitor.check_health()
# Returns:
{
    "status": "healthy|degraded|error",
    "last_check": timestamp,
    "current_time": timestamp,
    "metrics": {...}
}
```

## Performance Monitoring

The performance monitoring system provides:
- Dynamic sampling rate adjustment
- Request duration tracking
- Error rate monitoring
- Slow request detection

See `monitoring.py` for implementation details.

## Security

- Configuration values are validated for security requirements
- Secret keys are checked for minimum length and complexity
- Version mismatches are tracked to prevent security issues
- Environment-specific validation rules are enforced
