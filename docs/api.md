# JSquared API Documentation

## Overview

JSquared provides a RESTful API built with FastAPI. The API uses JWT for authentication and implements rate limiting to prevent abuse.

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses OAuth2 with JWT tokens for authentication. All authenticated endpoints require a Bearer token in the Authorization header.

### Endpoints

#### Login
- **URL**: `/api/v1/auth/token`
- **Method**: `POST`
- **Rate Limit**: 5 requests per minute
- **Request Body**:
  ```json
  {
    "username": "user@example.com",
    "password": "userpassword"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJ0eXAi...",
    "refresh_token": "eyJ0eXAi...",
    "token_type": "bearer"
  }
  ```

#### Register
- **URL**: `/api/v1/auth/register`
- **Method**: `POST`
- **Rate Limit**: 5 requests per minute
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "userpassword",
    "confirm_password": "userpassword",
    "full_name": "John Doe"
  }
  ```
- **Response**: User object

#### Get Current User
- **URL**: `/api/v1/auth/me`
- **Method**: `GET`
- **Rate Limit**: 5 requests per minute
- **Authentication**: Required
- **Response**: User object

## Rate Limiting

### Overview
The API implements rate limiting to prevent abuse and ensure fair usage. Rate limits are enforced per IP address and endpoint.

### Rate Limit Categories

1. **Authentication Endpoints** (`auth_rate_limit`)
   - Limit: 5 requests per minute
   - Applies to: `/auth/token`, `/auth/register`, `/auth/me`
   - Purpose: Prevent brute force attacks

2. **Standard API Endpoints** (`api_rate_limit`)
   - Limit: 60 requests per minute
   - Purpose: General API usage

3. **Heavy Operations** (`heavy_operation_rate_limit`)
   - Limit: 10 requests per minute
   - Purpose: Resource-intensive operations

### Rate Limit Headers

When a request is made, the following headers are included in the response:

```
X-RateLimit-Limit: Maximum requests allowed
X-RateLimit-Remaining: Remaining requests in the current window
X-RateLimit-Reset: Timestamp when the rate limit resets
```

### Rate Limit Exceeded Response

When rate limit is exceeded, the API returns:

- **Status Code**: 429 Too Many Requests
- **Response Body**:
  ```json
  {
    "detail": "Too many requests",
    "retry_after": 60
  }
  ```
- **Headers**:
  ```
  Retry-After: Seconds until the rate limit resets
  ```

## Testing

### Rate Limit Testing Script

Location: `server/scripts/test_rate_limits.sh`

This script tests rate limiting functionality:
1. Tests authentication rate limits
2. Tests API endpoint rate limits
3. Verifies rate limit headers and responses

Run the script:
```bash
./server/scripts/test_rate_limits.sh
```

## Dependencies

- FastAPI: Web framework
- Redis: Rate limit storage
- PostgreSQL: Database
- Python 3.11+

## Development Setup

1. Install dependencies:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. Start Redis:
   ```bash
   brew services start redis
   ```

3. Run the server:
   ```bash
   cd server
   PYTHONPATH=/path/to/jsquared/server uvicorn app.main:app --reload
   ```

## API Documentation UI

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Error Handling

### Common HTTP Status Codes

- 200: Success
- 401: Unauthorized
- 422: Validation Error
- 429: Too Many Requests

### Error Response Format

```json
{
  "detail": "Error message"
}
```

## Security Best Practices

1. Use HTTPS in production
2. Store tokens securely
3. Implement token refresh flow
4. Monitor rate limit violations
5. Regular security audits
