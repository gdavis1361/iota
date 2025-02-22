# Configuration Setup Guide

## Overview

This guide covers the configuration system setup and management for IOTA. The configuration system uses environment-based settings with strict validation and secure handling of sensitive values.

## Environment Configuration

### Required Environment Variables

```bash
# Core Settings
export ENVIRONMENT=development  # Options: development|testing|staging|production
export SECRET_KEY="your-32-char-secret-key"  # Must be at least 32 characters

# Database Configuration
export POSTGRES_PASSWORD="your_secure_password"
export POSTGRES_DB="your_database_name"
export POSTGRES_USER="your_database_user"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT=5432

# Redis Configuration
export REDIS_HOST="localhost"
export REDIS_PORT=6379
export REDIS_PASSWORD="your_redis_password"
```

### Optional Environment Variables

```bash
# Performance Settings
export SAMPLING_WINDOW_SECONDS=3600  # Default: 1 hour
export SLOW_REQUEST_THRESHOLD_MS=1000  # Default: 1 second
export ERROR_RATE_THRESHOLD=0.1  # Default: 10%
export SLOW_RATE_THRESHOLD=0.1  # Default: 10%

# Security Settings
export ALLOWED_HOSTS="localhost,example.com"
export DEBUG=false  # Default: false in production
```

## Configuration Files

### Location
Configuration files are stored in the `server/core/config` directory:

```python
from pathlib import Path

CONFIG_DIR = Path("server/core/config")
CONFIG_FILES = {
    "base": CONFIG_DIR / "base.py",
    "development": CONFIG_DIR / "development.py",
    "production": CONFIG_DIR / "production.py",
    "testing": CONFIG_DIR / "testing.py"
}
```

### Configuration Classes

1. **EnvironmentType (Enum)**
   ```python
from enum import Enum

class EnvironmentType(Enum):
    development = "development"
    testing = "testing"
    staging = "staging"
    production = "production"
```

2. **Settings (BaseSettings)**
   ```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: EnvironmentType
    SECRET_KEY: str
    POSTGRES_PASSWORD: str
    # ... other settings
```

## Validation Rules

### Secret Key
- Minimum length: 32 characters
- Must contain: letters, numbers, and symbols
- Must not be a common password

### Database Credentials
- Passwords must meet complexity requirements
- Host must be valid hostname or IP
- Port must be within valid range (1-65535)

### Performance Thresholds
- Must be positive numbers
- Rate thresholds must be between 0 and 1
- Time thresholds in milliseconds

## Environment-Specific Configuration

### Development
```bash
export ENVIRONMENT=development
export DEBUG=true
export ALLOWED_HOSTS="localhost,127.0.0.1"
```

### Testing
```bash
export ENVIRONMENT=testing
export DEBUG=false
export SECRET_KEY="test_secret_key_32chars_long_enough"
export POSTGRES_PASSWORD="test_password"
export POSTGRES_DB="test_db"
```

### Production
```bash
export ENVIRONMENT=production
export DEBUG=false
export ALLOWED_HOSTS="your.domain.com"
# Ensure all credentials are secure production values
```

## Security Considerations

### Credential Management
1. Never commit credentials to version control
2. Use environment variables for sensitive values
3. Consider using a secret management service in production

### Environment Isolation
1. Use different databases for each environment
2. Maintain separate Redis instances
3. Never share credentials between environments

## Testing Configuration

### Configuration Tests
```python
def test_settings_validation():
    """Test settings validation rules."""
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="invalid",
            SECRET_KEY="too_short",
            POSTGRES_PASSWORD=""
        )

def test_environment_specific_settings():
    """Test environment-specific configuration."""
    settings = create_test_settings()
    assert settings.ENVIRONMENT == EnvironmentType.testing
    assert len(settings.SECRET_KEY) >= 32
```

## Troubleshooting

### Common Issues

1. **Invalid Environment**
   ```
   Error: "invalid environment: 'dev'"
   Fix: Use valid environment type (development, testing, staging, production)
   ```

2. **Secret Key Too Short**
   ```
   Error: "secret_key length < 32 characters"
   Fix: Provide a secret key with at least 32 characters
   ```

3. **Missing Required Variables**
   ```
   Error: "field required: POSTGRES_PASSWORD"
   Fix: Ensure all required environment variables are set
   ```

## Best Practices

1. **Environment Variables**
   - Use `.env` file for development
   - Never commit `.env` files
   - Document all variables

2. **Security**
   - Regular credential rotation
   - Environment isolation
   - Secure credential storage

3. **Testing**
   - Test all validation rules
   - Verify environment isolation
   - Check security constraints

## References

- [Configuration Management ADR](/Users/allan/Projects/iota/docs/config/../adr/0001-configuration-management.md)
- [Development Guide](/Users/allan/Projects/iota/docs/config/../development.md)
- [Security Policy](/Users/allan/Projects/iota/docs/config/../security.md)
