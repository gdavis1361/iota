# Rate Limiting Implementation Guide

## Overview

This document details the implementation of rate limiting in the JSquared API.

## Implementation Details

### Core Components

1. **Redis Storage**
   - Used for storing rate limit counters
   - Each counter has a 60-second expiry
   - Key format: `rate_limit:{ip}:{function_name}`

2. **Rate Limit Decorator**
   - Location: `server/app/core/rate_limit.py`
   - Implements a custom decorator for FastAPI endpoints
   - Supports different rate limit categories

### Rate Limit Categories

1. **Authentication Rate Limit**
```python
from fastapi import Depends
from server.core.rate_limit import auth_rate_limit
from typing import Dict

@auth_rate_limit()  # 5 requests/minute
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """Handle user login and token generation."""
    return await process_login(form_data)
```

2. **Standard API Rate Limit**
```python
from fastapi import APIRouter
from server.core.rate_limit import api_rate_limit
from typing import Dict, Any

@api_rate_limit()  # 60 requests/minute
async def standard_endpoint() -> Dict[str, Any]:
    """Handle standard API request."""
    return {"status": "success"}
```

3. **Heavy Operation Rate Limit**
```python
from server.core.rate_limit import heavy_operation_rate_limit
from typing import Dict, Any

@heavy_operation_rate_limit()  # 10 requests/minute
async def resource_intensive_operation() -> Dict[str, Any]:
    """Handle resource-intensive operation."""
    return await process_heavy_task()
```

## Code Structure

### Rate Limit Module (`rate_limit.py`)

```python
from typing import Callable, Dict, Any
from functools import wraps
from fastapi import Request
import redis

def rate_limit(calls: int, period: str) -> Callable:
    """Base rate limit decorator.

    Args:
        calls: Number of allowed calls per period
        period: Time period for rate limit (e.g., "1m", "1h")

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                return await func(*args, **kwargs)

            # Generate unique key
            key = f"rate_limit:{request.client.host}:{func.__name__}"

            # Check and update rate limit
            current = int(redis_client.get(key) or 0)
            if current >= calls:
                return rate_limit_exceeded_response()

            # Update counter
            pipe = redis_client.pipeline()
            if current == 0:
                pipe.setex(key, 60, 1)
            else:
                pipe.incr(key)
            pipe.execute()

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

## Testing

### Test Script (`test_rate_limits.sh`)

The test script performs:
1. Authentication endpoint tests
2. API endpoint tests
3. Rate limit verification

```bash
#!/bin/bash

# Test auth rate limit
for i in {1..6}; do
    curl -X POST http://localhost:8000/api/v1/auth/token \
         -d "username=test@example.com&password=test"
    sleep 1
done

# Test API rate limit
TOKEN="..."
for i in {1..61}; do
    curl -H "Authorization: Bearer $TOKEN" \
         http://localhost:8000/api/v1/auth/me
    sleep 0.1
done
```

## Monitoring and Maintenance

### Redis Monitoring

1. Check current rate limit counters:
   ```bash
   redis-cli keys "rate_limit:*"
   ```

2. Get counter value:
   ```bash
   redis-cli get "rate_limit:127.0.0.1:login_access_token"
   ```

3. Clear all rate limits:
   ```bash
   redis-cli del "rate_limit:*"
   ```

### Best Practices

1. **Regular Monitoring**
   - Monitor rate limit violations
   - Track endpoint usage patterns
   - Adjust limits based on usage

2. **Error Handling**
   - Proper error messages
   - Retry-After headers
   - Rate limit headers

3. **Client Guidelines**
   - Implement exponential backoff
   - Respect rate limit headers
   - Cache responses when possible

## Future Improvements

1. **Dynamic Rate Limits**
   - Adjust based on server load
   - User-specific limits
   - Time-based variations

2. **Enhanced Monitoring**
   - Rate limit violation alerts
   - Usage analytics
   - Performance impact tracking

3. **Additional Features**
   - Token bucket algorithm
   - Rate limit by user/API key
   - Bulk operation endpoints
