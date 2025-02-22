# Authentication Guide

## Overview
This guide explains the authentication system used in the IOTA project, including setup, configuration, and best practices.

## Authentication Flow

### 1. API Key Authentication
- Used for service-to-service communication
- Requires valid API key in `Authorization` header
- Keys are environment-specific and rotated regularly

Example:
```python
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://api.example.com/v1/data", headers=headers)
```

### 2. User Authentication
- JWT-based authentication for user sessions
- Supports OAuth2 providers (configurable)
- Implements refresh token rotation

Configuration:
```python
from server.core.config.base import Config

config = Config()
assert config.AUTH_SECRET_KEY, "Authentication secret key must be set"
assert len(config.AUTH_SECRET_KEY) >= 32, "Auth key must be at least 32 characters"
```

## Security Considerations

### Secret Management
- Never commit secrets to version control
- Use environment variables for sensitive values
- Rotate secrets regularly
- Monitor for exposed secrets

### Key Requirements
- API keys: 32+ random characters
- JWT secret: 32+ random characters
- Refresh tokens: 64+ random characters

### Environment Variables
```bash
# Required for authentication
AUTH_SECRET_KEY=your-secret-key
AUTH_TOKEN_EXPIRE_MINUTES=60
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional OAuth settings
OAUTH_GITHUB_CLIENT_ID=your-github-client-id
OAUTH_GITHUB_CLIENT_SECRET=your-github-client-secret
```

## Error Handling

### Common Issues
1. Invalid API Key
   ```json
   {
     "error": "invalid_auth",
     "message": "Invalid API key provided",
     "status_code": 401
   }
   ```

2. Expired Token
   ```json
   {
     "error": "token_expired",
     "message": "Authentication token has expired",
     "status_code": 401
   }
   ```

3. Invalid Token
   ```json
   {
     "error": "invalid_token",
     "message": "Invalid authentication token",
     "status_code": 401
   }
   ```

### Error Resolution
1. Check environment variables are set correctly
2. Verify API key is valid and not expired
3. Ensure clock sync between services
4. Check for proper header formatting

## Monitoring & Alerts

### Metrics
- Failed authentication attempts
- Token expiration events
- API key usage patterns
- OAuth provider status

### Alert Rules
1. High authentication failure rate
2. Unusual API key usage patterns
3. OAuth provider connectivity issues

## Testing

### Unit Tests
```python
def test_api_key_validation():
    """Test API key validation logic."""
    assert validate_api_key("valid-key") is True
    assert validate_api_key("invalid-key") is False

def test_jwt_token_creation():
    """Test JWT token creation and validation."""
    token = create_jwt_token({"user_id": 123})
    payload = validate_jwt_token(token)
    assert payload["user_id"] == 123
```

### Integration Tests
See [Integration Testing Guide](/Users/allan/Projects/iota/docs/../tests/integration/README.md) for authentication integration tests.

## Related Documentation
- [Authorization Guide](/Users/allan/Projects/iota/docs/authorization.md)
- [Security Guidelines](/Users/allan/Projects/iota/docs/../tests/scripts/SECURITY.md)
- [Configuration Management](/Users/allan/Projects/iota/docs/adr/0001-configuration-management.md)
- [Integration Testing](/Users/allan/Projects/iota/docs/../tests/integration/README.md)
