# Configuration Parser

## Overview

The configuration parser is a custom implementation for loading and validating environment variables. It provides better control and error handling compared to external dependencies like python-dotenv.

## Design Principles

1. **Simplicity Over Complexity**
   - Direct environment variable access
   - Clear validation rules
   - Minimal dependencies

2. **Comprehensive Error Handling**
   - Detailed error messages
   - Validation at multiple levels
   - Clear error resolution steps

3. **Type Safety**
   - Strong typing using Pydantic
   - Runtime type checking
   - Conversion handling

## Implementation

### Core Components

1. **Environment Type Enum**
```python
from enum import Enum

class EnvironmentType(Enum):
    development = "development"
    testing = "testing"
    staging = "staging"
    production = "production"

    @classmethod
    def _missing_(cls, value: str) -> Optional["EnvironmentType"]:
        """Handle missing enum values with helpful error."""
        valid_values = [e.value for e in cls]
        raise ValueError(
            f"Invalid environment: '{value}'. "
            f"Must be one of: {', '.join(valid_values)}"
        )
```

2. **Settings Model**
```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Configuration settings with validation."""

    ENVIRONMENT: EnvironmentType
    SECRET_KEY: str

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key length and complexity."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
```

3. **Settings Factory**
```python
def create_settings(env_file: Optional[str] = None) -> Settings:
    """Create settings instance with optional env file."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as e:
        logger.error("Configuration validation failed", error=str(e))
        raise
```

## Usage Examples

### Basic Usage
```python
from server.core.config import create_settings

# Load from environment
settings = create_settings()

# Load from specific file
settings = create_settings(".env.test")

# Access settings
env = settings.ENVIRONMENT
is_prod = env == EnvironmentType.production
```

### Error Handling
```python
try:
    settings = create_settings()
except ValidationError as e:
    logger.error("Invalid configuration", error=str(e))
    sys.exit(1)
```

### Testing
```python
def test_settings_validation():
    """Test configuration validation."""
    with pytest.raises(ValidationError) as exc:
        Settings(
            ENVIRONMENT="invalid",
            SECRET_KEY="short"
        )
    assert "Invalid environment" in str(exc.value)
    assert "SECRET_KEY must be at least 32 characters" in str(exc.value)
```

## Error Messages

### Common Errors

1. **Invalid Environment**
```
Error: Invalid environment: 'dev'. Must be one of: development, testing, staging, production
Solution: Use a valid environment name from the allowed list
```

2. **Missing Required Field**
```
Error: field required (type=value_error.missing)
Solution: Ensure all required environment variables are set
```

3. **Invalid Type**
```
Error: value is not a valid integer (type=type_error.integer)
Solution: Provide correct type for the configuration value
```

## Logging

### Log Levels

1. **ERROR**
   - Configuration validation failures
   - Missing required variables
   - Type conversion errors

2. **WARNING**
   - Deprecated settings usage
   - Non-optimal configurations
   - Security recommendations

3. **INFO**
   - Configuration loading
   - Environment detection
   - Successful validation

4. **DEBUG**
   - Detailed validation steps
   - Variable resolution
   - Type conversion details

### Example Log Output
```
[ERROR] Configuration validation failed
  error="Invalid environment: 'dev'"
  valid_values="development, testing, staging, production"
```

## Best Practices

1. **Configuration Loading**
   - Load early in application startup
   - Fail fast on validation errors
   - Log comprehensive error details

2. **Error Handling**
   - Catch ValidationError at top level
   - Provide clear error messages
   - Include resolution steps

3. **Testing**
   - Test all validation rules
   - Verify error messages
   - Check edge cases

## References

- [Configuration Setup](/Users/allan/Projects/iota/docs/config/setup.md)
- [Error Logger](/Users/allan/Projects/iota/docs/error_logger.md)
- [Architecture Overview](/Users/allan/Projects/iota/docs/architecture.md)
