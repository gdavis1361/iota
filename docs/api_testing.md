# API Testing Guide

## Rate Limiting Tests

### Authentication Rate Limiting (5 requests/minute)

Test using curl:
```bash
# Test login endpoint rate limit
for i in {1..6}; do
    curl -X POST http://localhost:8000/api/v1/auth/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=testpassword123" \
    && echo "\nRequest $i complete" \
    && sleep 1
done

# Test registration endpoint rate limit
for i in {1..6}; do
    curl -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test'$i'@example.com","password":"testpass123","full_name":"Test User"}' \
    && echo "\nRequest $i complete" \
    && sleep 1
done
```

Expected behavior:
- First 5 requests should succeed
- 6th request should return 429 Too Many Requests
- Response headers will include:
  - X-RateLimit-Limit: 5
  - X-RateLimit-Remaining: 0
  - X-RateLimit-Reset: (timestamp)

### Standard API Rate Limiting (60 requests/minute)

Test using curl:
```bash
# First, get a valid JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
- H "Content-Type: application/x-www-form-urlencoded" \
- d "username=test@example.com&password=testpassword123" | jq -r .access_token)

# Test /me endpoint rate limit
for i in {1..61}; do
    curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me \
    && echo "\nRequest $i complete" \
    && sleep 0.1
done
```

Expected behavior:
- First 60 requests should succeed
- 61st request should return 429 Too Many Requests

### Using Artillery for Load Testing

Install Artillery:
```bash
npm install -g artillery
```

Create a test file (rate_limit_test.yml):
```yaml
config:
  target: "http://localhost:8000"
  phases:
    - duration: 60
      arrivalRate: 2
  defaults:
    headers:
      Content-Type: "application/json"
scenarios:
  - name: "Test auth rate limiting"
    flow:
      - post:
          url: "/api/v1/auth/token"
          form:
            username: "test@example.com"
            password: "testpassword123"
```

Run the test:
```bash
artillery run rate_limit_test.yml
```

## Monitoring Rate Limits

### Check Current Rate Limit Status

```bash
# Check headers for rate limit information
curl -I -X POST http://localhost:8000/api/v1/auth/token \
- H "Content-Type: application/x-www-form-urlencoded" \
- d "username=test@example.com&password=testpassword123"
```

### Rate Limit Headers

All rate-limited endpoints return these headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in the window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Troubleshooting

1. If you hit a rate limit:
   - Wait for the rate limit window to reset (1 minute)
   - Check the `X-RateLimit-Reset` header for exact reset time

2. Common HTTP Status Codes:
   - 200: Successful request
   - 429: Too Many Requests (rate limit exceeded)
   - 401: Unauthorized (invalid credentials)
   - 403: Forbidden (valid credentials but insufficient permissions)
