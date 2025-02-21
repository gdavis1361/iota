# Iota Configuration Management

## Overview
The configuration management system provides robust validation and type conversion for application settings. It uses Pydantic for validation and supports environment-based configuration with strong security defaults.

## Environment Variables

### Required Settings
- `SECRET_KEY`: Application secret key (min. 32 characters)
- `APP_NAME`: Application name (default: "iota")

### Environment Settings
- `ENVIRONMENT`: Application environment (development, staging, production, test)
- `DEBUG`: Debug mode flag (default: False)
- `LOG_LEVEL`: Logging level (default: "INFO")
- `LOG_FORMAT`: Log format - json or console (default: "json")
- `ALLOWED_HOSTS`: List of allowed hosts (default: ["*"], must be specific hosts in production)

### Sentry Integration
- `SENTRY_ENABLED`: Enable Sentry integration (default: False)
- `SENTRY_DSN`: Sentry DSN (required if Sentry enabled)
- `SENTRY_ENVIRONMENT`: Environment for Sentry (default: "development")
- `SENTRY_DEBUG`: Enable Sentry debug mode (default: False)
- `SENTRY_TRACES_SAMPLE_RATE`: Sample rate for traces (0.0-1.0, default: 0.1)
- `SENTRY_PROFILES_SAMPLE_RATE`: Sample rate for profiles (0.0-1.0, default: 0.1)
- `SENTRY_MAX_BREADCRUMBS`: Maximum breadcrumbs (default: 100)
- `SENTRY_METADATA`: Additional Sentry metadata (JSON string)

### Performance Monitoring
- `SLOW_REQUEST_THRESHOLD_MS`: Threshold for slow requests in ms (default: 1000.0)
- `ERROR_RATE_THRESHOLD`: Error rate threshold (0.0-1.0, default: 0.1)
- `SLOW_RATE_THRESHOLD`: Slow request rate threshold (0.0-1.0, default: 0.1)

## Validation Rules

### Security Validation
1. SECRET_KEY:
   - Must be at least 32 characters long
   - Required in all environments
   - No default value provided

2. Environment:
   - Must be one of: development, staging, production, test
   - Case-insensitive validation
   - Defaults to "development"

3. Allowed Hosts:
   - Wildcard (*) only allowed in non-production
   - Must specify explicit hosts in production
   - JSON array format in environment variable

### Rate Value Validation
All rate values must be between 0 and 1:
- SENTRY_TRACES_SAMPLE_RATE
- SENTRY_PROFILES_SAMPLE_RATE
- ERROR_RATE_THRESHOLD
- SLOW_RATE_THRESHOLD

### Sentry Configuration
1. DSN Format:
   - Required when Sentry is enabled
   - Must match pattern: https://<key>@<host>/<project-id>

2. Metadata:
   - Must be valid JSON if provided
   - Optional, defaults to empty dict
   - Validated during settings initialization

## CLI Validation Tool

The `validate_config.py` tool helps verify your configuration before deployment:

```bash
python validate_config.py [--env ENV_FILE]
```

### Features
- Environment file loading and validation
- Detailed error reporting
- Configuration state logging
- Performance metrics display

### Environment File Format
```
# Required Settings
APP_NAME=iota
SECRET_KEY=your-secret-key-min-32-chars

# Environment Settings
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_HOSTS=["localhost"]

# Optional Sentry Settings
SENTRY_ENABLED=false
SENTRY_DSN=https://your-dsn
```

Note: Environment variables should be specified without quotes unless they contain special characters or are JSON strings (like ALLOWED_HOSTS).

### Error Messages

Common validation errors and their solutions:

1. SECRET_KEY too short:
   ```
   SECRET_KEY must be at least 32 characters long
   ```
   Solution: Use a longer secret key

2. Invalid environment:
   ```
   Invalid environment 'invalid'. Must be one of development, production, staging, test
   ```
   Solution: Use one of the allowed environment values

3. Invalid JSON format:
   ```
   Error parsing value for field "ALLOWED_HOSTS"
   ```
   Solution: Ensure JSON strings are properly formatted (e.g., `["host1", "host2"]`)

### Logging

The tool provides structured logging at different levels:

- INFO: Configuration state, validation success
- ERROR: Validation failures, file loading errors
- DEBUG: Detailed validation steps (when DEBUG=true)

Example success output:
```
INFO - Configuration validation successful!
INFO - Current configuration:
INFO -   Environment: development
INFO -   Debug Mode: False
INFO -   Log Level: INFO
...
```

## Error Messages

Common validation errors and their meanings:

```
SECRET_KEY must be at least 32 characters long
- Cause: SECRET_KEY is too short
- Fix: Provide a key with ≥32 characters

Invalid environment '{value}'
- Cause: Environment not in allowed list
- Fix: Use development, staging, production, or test

Invalid Sentry DSN format
- Cause: DSN doesn't match required pattern
- Fix: Use format https://<key>@<host>/<project-id>

Rate value must be between 0 and 1
- Cause: Rate value outside valid range
- Fix: Provide value between 0.0 and 1.0
```

## Testing

The configuration system includes comprehensive tests in `tests/core/test_config.py`. Key test areas:

1. Settings Singleton
2. Environment Validation
3. Sentry Configuration
4. Security Settings
5. Rate Value Validation
6. Default Values
7. Mandatory Fields

### Test Environment Setup

Tests use a fixture that:
1. Backs up current environment
2. Sets test values
3. Runs test
4. Restores original environment
5. Ensures valid SECRET_KEY present

## Best Practices

1. Security:
   - Never commit SECRET_KEY to version control
   - Use specific ALLOWED_HOSTS in production
   - Rotate secrets regularly

2. Configuration:
   - Use environment variables for configuration
   - Validate all inputs
   - Provide clear error messages

3. Testing:
   - Maintain test isolation
   - Test both valid and invalid cases
   - Verify error messages exactly

## Troubleshooting

1. Settings validation fails:
   - Check environment variables match required formats
   - Verify SECRET_KEY length
   - Ensure rate values are between 0-1
   - Validate JSON strings are properly formatted

2. Test failures:
   - Ensure test fixture properly cleans environment
   - Verify expected error messages match exactly
   - Check for environment variable conflicts
