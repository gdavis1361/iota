# JSquared Project

A modern web application with multiple interfaces and robust authentication.

![CI Tests](https://github.com/gdavis1361/iota/actions/workflows/ci-test.yml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type checked with mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)

## Project Structure

```
jsquared/
├── server/              # FastAPI backend server
├── admin-client/        # Admin interfaces
│   ├── src/next/       # Next.js admin interface
│   └── src/python/     # Python admin interface
└── client/             # Future client applications
```

## Components

### 1. FastAPI Backend (Port 8000)

The main backend server providing REST API endpoints.

#### Setup and Running
```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Database Migrations
Migration files are located in:
- `server/migrations/versions/` (Active migrations)
- `server/alembic/versions/` (Additional migrations)

To run migrations:
```bash
cd server
alembic upgrade head
```

### 2. Next.js Admin Client (Port 3000)

A modern React-based admin interface.

#### Setup and Running
```bash
cd admin-client/src/next
npm install
npm run dev
```

Access at http://localhost:3000

### 3. Python Admin Client (Port 3001)

A server-rendered admin interface using FastAPI and Jinja2 templates.

#### Setup and Running
```bash
cd admin-client/src/python
pip install -r requirements.txt
uvicorn app.main:app --reload --port 3001
```

Access at http://localhost:3001

## Authentication

All interfaces use the same authentication system:

### Default Test Account
- Email: test@example.com
- Password: testpassword123

### Endpoints
- Register: POST /api/v1/auth/register
- Login: POST /api/v1/auth/token
- Profile: GET /api/v1/auth/me

## Rate Limiting

The application implements a multi-layer rate limiting strategy:

### 1. Nginx Rate Limiting (Infrastructure Level)

Nginx provides the first layer of rate limiting at the infrastructure level:

```nginx
# Global rate limit settings in nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Applied in location blocks in jsquared.conf
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # ... other configurations
}
```

- Base Rate: 10 requests per second
- Burst Allowance: 20 additional requests
- Scope: IP-based, applies to all API endpoints
- Memory Zone: 10MB for storing rate limit states

### 2. FastAPI Rate Limiting (Application Level)

The application implements more granular rate limiting using slowapi:

1. Authentication Endpoints:
   - Login: 5 attempts per minute
   - Register: 5 attempts per minute
   - Prevents brute force attacks

2. Standard API Endpoints:
   - 60 requests per minute per IP
   - Applies to general API operations

3. Resource-Intensive Operations:
   - 10 requests per minute per IP
   - Applies to computationally expensive endpoints

### Rate Limit Response Headers

When rate limits are exceeded, the API returns:
- Status Code: 429 Too Many Requests
- Headers:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in the window
  - `X-RateLimit-Reset`: Time when the rate limit resets

### Monitoring and Adjustment

Rate limits can be adjusted in:
1. Nginx configuration: `/opt/homebrew/etc/nginx/nginx.conf`
2. Application code: `server/app/core/rate_limit.py`

## Observability

IOTA includes comprehensive observability features using OpenTelemetry for distributed tracing and Prometheus/Grafana for metrics and monitoring. For detailed information, see our [Observability Guide](docs/observability.md).

### Quick Start

1. Start monitoring services:
```bash
docker-compose up -d prometheus grafana
```

2. Import Grafana dashboard:
   - Open Grafana at http://localhost:3000
   - Navigate to Dashboards > Import
   - Upload `monitoring/grafana/rate_limiter_dashboard.json`

### Key Metrics

Monitor these metrics in production:
- Rate limiter response time (target: < 1ms)
- Redis operation latency (target: < 3ms)
- Error rates (target: 0)
- Request throughput

### Alert Rules

Configured alerts:
- High latency (> 1ms for 5m)
- Redis errors (any in 1m)
- High rejection rate (> 20% for 5m)
- Low throughput (< 10 RPS for 5m)
- High memory usage (> 1GB for 5m)

See [Alert Rules](monitoring/prometheus/alert_rules.yml) for details.

### Distributed Tracing

Key trace points:
- Rate limit checks
- Redis operations
- Configuration loading

Configure sampling rates:
- Development: 100% (default)
- Production: 10% recommended

## Performance Testing and Monitoring

IOTA includes comprehensive performance testing and monitoring capabilities. For detailed information, see our [Performance Testing Guide](docs/performance_testing.md).

### Running Performance Tests

1. Ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
```

2. Run the performance test suite:
```bash
pytest tests/performance/test_rate_limiter.py --benchmark-only -v
```

### Performance Thresholds

Our CI pipeline enforces these performance thresholds:
- Rate limiter single operation: < 1ms
- Redis operations (set+get+delete): < 3ms
- Configuration load time: < 5ms
- Memory usage per rate limit key: < 100 bytes

### Monitoring Guidelines

Monitor these key metrics in production:
- Rate limiter response time
- Redis CPU and memory usage
- Request throughput
- Error rates

Alert thresholds:
- Redis CPU usage > 80%
- Redis memory usage > 90%
- Rate limit check latency > 10ms
- Error rate > 1%

### CI/CD Integration

Performance tests run automatically on:
- Push to main branch
- Pull requests to main branch

Failed performance tests block merging to maintain performance standards.

See [GitHub Actions Performance Workflow](.github/workflows/performance-tests.yml) for implementation details.

## System Complexity Analysis

Ranking of system components from easiest to most complex to implement and maintain:

### 1. FastAPI Backend (Easiest)
- Straightforward REST API implementation
- Clear documentation with automatic Swagger/ReDoc
- Simple dependency management
- Intuitive routing and middleware

### 2. Docker Configuration
- Standard container configurations
- Well-documented Docker Compose setup
- Clear network and volume management
- Some complexity with multi-service orchestration

### 3. Redis Sentinel (Moderate)
- Initial setup is straightforward
- Configuration requires careful planning
- Failover mechanics need thorough testing
- Network configuration needs attention
- Requires understanding of Redis replication

### 4. Monitoring Stack (Most Complex)
- Multiple components (Prometheus, Grafana, Exporters)
- Complex configuration for metrics collection
- Time-consuming dashboard setup
- Alert rule management is tedious
- Steep learning curve for visualization tools

Alternative monitoring solutions worth considering:
1. DataDog - Simpler setup, managed service
2. New Relic - Good Redis integration
3. Redis Enterprise - Built-in monitoring
4. Redis Insight - Dedicated Redis monitoring
5. Elastic Stack - More intuitive setup

## Redis Sentinel Cluster

High-availability Redis cluster with Sentinel for automatic failover.

### Components
- Redis Master (Port 6379)
- Redis Replicas (Ports 6380, 6381)
- Redis Sentinels (Ports 26379-26381)

Detailed documentation:
- [Redis Sentinel Setup](redis/README.md)
- [Docker Configuration](docker/README.md)

### Starting the Cluster
```bash
cd redis
docker compose up -d
```

## Monitoring Stack

Comprehensive monitoring using Prometheus and Grafana.

### Components
- Prometheus (Port 9090)
- Grafana (Port 3000)
- Redis Exporters (Ports 9121, 9122)

Detailed documentation:
- [Monitoring Setup](monitoring/README.md)
- [Docker Configuration](docker/README.md)

### Starting Monitoring
```bash
cd monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

### Access Points
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

## Development Setup

1. Start the backend server (Port 8000)
```bash
cd server
uvicorn app.main:app --reload --port 8000
```

2. Start the Next.js admin client (Port 3000)
```bash
cd admin-client/src/next
npm run dev
```

3. Start the Python admin client (Port 3001)
```bash
cd admin-client/src/python
uvicorn app.main:app --reload --port 3001
```

## Database

Using PostgreSQL with SQLAlchemy ORM.

### Models
- User: Authentication and user management
  - Fields: id, email, hashed_password, full_name, is_active, is_verified, role, created_at, updated_at, last_login

### Migration Files
1. Active Migrations (`server/migrations/versions/`):
   - 20250206_231505_initial_migration.py
   - 20250207_000455_recreate_tables.py
   - 20250207_011419_create_users_table.py
   - 20250207_011545_create_users_table.py

2. Additional Migrations (`server/alembic/versions/`):
   - initial_migration.py

## Configuration

IOTA uses Pydantic v2 for configuration management, providing type-safe settings with comprehensive validation.

### Environment Variables

Required environment variables:
```bash
# Application Environment
ENVIRONMENT=development  # Options: development, testing, staging, production

# Security
SECRET_KEY=your-secret-key  # Minimum 32 characters

# Database
POSTGRES_PASSWORD=your-db-password
POSTGRES_DB=your-db-name
POSTGRES_USER=postgres  # Optional, defaults to 'postgres'
POSTGRES_HOST=localhost  # Optional, defaults to 'localhost'
POSTGRES_PORT=5432  # Optional, defaults to 5432

# Redis
REDIS_HOST=localhost  # Optional, defaults to 'localhost'
REDIS_PORT=6379  # Optional, defaults to 6379
REDIS_PASSWORD=  # Optional
```

### Rate Limiting

Rate limiting is configured through the settings system. Default configuration:

```python
RateLimitConfig(
    default_window=60,  # Default time window in seconds
    default_max_requests=100,  # Default max requests per window
    endpoint_limits={  # Optional endpoint-specific limits
        "/api/endpoint": EndpointLimit(
            window=30,
            max_requests=50
        )
    }
)
```

Rate limit headers in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Seconds until window reset
- `Retry-After`: Present when rate limited

### Testing

For testing, use the provided test configuration helper:

```python
from server.core.config import create_test_settings

@pytest.fixture
def test_settings():
    return create_test_settings()
```

The test settings provide sensible defaults and proper test isolation.

## Documentation

### Development
- [Contributing Guidelines](docs/contributing.md)
- [Pre-commit Setup](docs/pre-commit.md)
- [Development Setup](docs/development.md)

### Architecture & Design
- [Configuration Management](docs/adr/0001-configuration-management.md)
- [Module Organization](docs/migration/001-module-consolidation.md)

### Security
- [Security Guidelines](tests/scripts/SECURITY.md)
- [Authentication](docs/authentication.md)
- [Authorization](docs/authorization.md)

### Testing
- [Testing Guide](docs/testing.md)
- [Performance Testing](tests/performance/README.md)
- [Integration Testing](tests/integration/README.md)

### Operations
- [Monitoring](docs/operations/monitoring.md)
- [Rate Limiting](docs/operations/rate_limiter.md)
- [Alerts](docs/operations/alerts.md)

## Future Enhancements

### Security & Rate Limiting
- [ ] Add detailed logging for rate limit events
- [ ] Create monitoring endpoint for rate limit status
- [ ] Implement IP allowlist/blocklist
- [ ] Add Two-Factor Authentication (2FA)
- [ ] Implement password complexity requirements
- [ ] Add session management and device tracking
- [ ] Implement API key authentication for external services

### Testing & Quality Assurance
- [ ] Add unit tests with pytest
- [ ] Set up integration tests
- [ ] Implement end-to-end testing
- [ ] Add load testing scripts
- [ ] Set up continuous integration (CI/CD)
- [ ] Add code coverage reporting
- [ ] Implement automated security scanning

### Performance Optimization
- [ ] Add Redis caching layer
- [ ] Implement database query optimization
- [ ] Add database connection pooling
- [ ] Set up content delivery network (CDN)
- [ ] Implement response compression
- [ ] Add database indexing strategy
- [ ] Set up database replication

### Monitoring & Logging
- [ ] Set up centralized logging (ELK Stack)
- [ ] Implement application performance monitoring (APM)
- [ ] Add error tracking (Sentry)
- [ ] Create system health dashboard
- [ ] Set up automated alerts
- [ ] Add request tracing
- [ ] Implement audit logging

### User Experience
- [ ] Add email verification
- [ ] Implement password reset functionality
- [ ] Create user profile management
- [ ] Add role-based access control (RBAC)
- [ ] Implement user preferences
- [ ] Add multi-language support
- [ ] Create mobile-responsive admin interface

### Documentation
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Create developer guide
- [ ] Write deployment documentation
- [ ] Add code documentation
- [ ] Create user guides
- [ ] Document database schema
- [ ] Add architecture diagrams

### DevOps & Infrastructure
- [ ] Set up Docker containerization
- [ ] Implement Kubernetes orchestration
- [ ] Add infrastructure as code (IaC)
- [ ] Set up backup and recovery procedures
- [ ] Implement blue-green deployment
- [ ] Add automated database migrations
- [ ] Set up development/staging/production environments

### Feature Enhancements
- [ ] Add batch processing capabilities
- [ ] Implement webhooks
- [ ] Add export/import functionality
- [ ] Create reporting module
- [ ] Implement file upload/download
- [ ] Add search functionality
- [ ] Create API versioning strategy

Note: These enhancements are suggestions for future development. Priorities should be set based on project requirements and user needs.
