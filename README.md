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

### Monitoring and Alerts

The application includes comprehensive monitoring with configurable alert thresholds:

#### Alert Thresholds

Default thresholds are defined in `scripts/monitoring/config.py` and can be overridden via environment variables:

#### Latency Thresholds
- Warning: > 1.0 ms (override: LATENCY_WARNING_MS)
- Critical: > 2.0 ms (override: LATENCY_CRITICAL_MS)

#### Memory Usage
- Warning: > 750 MB (override: MEMORY_WARNING_MB)
- Critical: > 1000 MB (override: MEMORY_CRITICAL_MB)

#### Rejection Rate
- Warning: > 10% (override: REJECTION_WARNING_PERCENT)
- Critical: > 20% (override: REJECTION_CRITICAL_PERCENT)

#### Redis Errors
- Warning: Any errors (override: REDIS_WARNING_ERRORS)
- Critical: > 1 error/min (override: REDIS_CRITICAL_ERRORS)

### Metric Collection

The monitoring system collects metrics with the following settings:
- Collection Interval: 5 minutes (override: METRIC_INTERVAL_MINUTES)
- Query Timeout: 30 seconds (override: METRIC_QUERY_TIMEOUT_SECONDS)
- Data Retention: 30 days (override: METRIC_RETENTION_DAYS)
- Resolution:
  - Last 24h: 1-minute intervals (override: METRIC_RESOLUTION_RECENT_MINUTES)
  - Historical: 5-minute intervals (override: METRIC_RESOLUTION_HISTORICAL_MINUTES)

### Alert Routing

Alerts are routed based on severity:

#### Critical Alerts (PagerDuty)
- Response Time: < 15 minutes
- Channel: PagerDuty + #incidents Slack
- Repeat Interval: 1 hour (override: CRITICAL_ALERT_REPEAT_HOURS)
- Auto-resolution: 24 hours (override: CRITICAL_ALERT_RESOLVE_HOURS)

#### Warning Alerts (Slack)
- Response Time: < 1 business hour
- Channel: #iota-alerts Slack
- Repeat Interval: 4 hours (override: WARNING_ALERT_REPEAT_HOURS)
- Auto-resolution: 7 days (override: WARNING_ALERT_RESOLVE_HOURS)

### Alert Grouping
- Wait Period: 30 seconds (override: ALERT_GROUP_WAIT_SECONDS)
- Group Interval: 5 minutes (override: ALERT_GROUP_INTERVAL_MINUTES)

### Example Configuration

To override default thresholds, set environment variables:

```bash
# Set stricter latency thresholds
export LATENCY_WARNING_MS=0.5
export LATENCY_CRITICAL_MS=1.0

# Adjust memory thresholds
export MEMORY_WARNING_MB=500
export MEMORY_CRITICAL_MB=750

# Configure alert routing
export CRITICAL_ALERT_REPEAT_HOURS=2
export WARNING_ALERT_REPEAT_HOURS=8
```

### Performance Reports

The system generates performance reports that include:
- Request rates and latencies
- Memory usage patterns
- Redis error rates
- Threshold violations

To generate a report:

```python
from scripts.monitoring.generate_performance_report import PerformanceReporter

reporter = PerformanceReporter("http://localhost:9090")
report = reporter.generate_report(duration_mins=60)
print(report)
```

For more details on monitoring and alerts, see our [Monitoring Guide](/Users/allan/Projects/iota/docs/monitoring.md).

## Monitoring

IOTA includes a comprehensive monitoring setup using Prometheus and Grafana:

- **Metrics**: Available at `http://localhost:8000/metrics/`
  - HTTP request counts and durations
  - Test execution metrics
  - System information

- **Prometheus**: Running on `http://localhost:9091`
  - Scrapes metrics every 15s
  - Configured alert rules for test latency
  - Dashboard available at `/graph`

- **Grafana**: Available at `http://localhost:3000`
  - Pre-configured Prometheus datasource
  - Test performance dashboards
  - Alert notifications

For detailed information about monitoring setup and available metrics, see [monitoring.md](/Users/allan/Projects/iota/docs/monitoring.md).

## Observability

IOTA includes comprehensive observability features using OpenTelemetry for distributed tracing and Prometheus/Grafana for metrics and monitoring. For detailed information, see our [Observability Guide](/Users/allan/Projects/iota/docs/observability.md).

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
- High CPU usage (> 80% for 5m)

See [Alert Rules](/Users/allan/Projects/iota/monitoring/prometheus/alert_rules.yml) for details.

### Distributed Tracing

Key trace points:
- Rate limit checks
- Redis operations
- Configuration loading

Configure sampling rates:
- Development: 100% (default)
- Production: 10% recommended

## Performance Testing and Monitoring

IOTA includes comprehensive performance testing and monitoring capabilities. For detailed information, see our [Performance Testing Guide](/Users/allan/Projects/iota/docs/performance_testing.md).

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

See [GitHub Actions Performance Workflow](/Users/allan/Projects/iota/.github/workflows/performance-tests.yml) for implementation details.

## Performance Monitoring

IOTA includes a comprehensive performance monitoring system that tracks operation durations, error rates, and identifies slow operations.

### Key Features

- High-precision timing (nanosecond accuracy)
- Automatic slow operation detection
- Thread-safe metric collection
- Persistent metric storage
- Aggregated statistics

### Usage

The monitoring system uses Python's context manager pattern for clean and reliable operation tracking:

```python
from server.core.monitoring import PerformanceMonitor

# Using context manager
with PerformanceMonitor().monitor("operation_name"):
    perform_operation()

# Direct metric recording
monitor = PerformanceMonitor()
monitor.record_version_bump(duration_ms=100)
monitor.record_changelog_update(duration_ms=50)
monitor.record_hook_installation(duration_ms=75)

# Retrieving metrics
stats = monitor.get_aggregated_stats("operation_name")
print(f"Error rate: {stats['error_rate']}")
print(f"Average duration: {stats['avg_duration']}ms")
```

### Configuration

Key settings that control monitoring behavior:

```python
# In server/core/config/base.py
SLOW_REQUEST_THRESHOLD_MS = 1000  # Mark operations over 1 second as slow
SAMPLING_WINDOW_SECONDS = 3600    # Keep last hour of metrics
ERROR_RATE_THRESHOLD = 0.1        # Alert if error rate exceeds 10%
```

### Metrics Storage

Metrics are stored in SQLite with the following schema:
- `operation`: Name of the monitored operation
- `timestamp`: Unix timestamp of the operation
- `duration`: Operation duration in milliseconds
- `error`: Boolean indicating if operation failed
- `is_slow`: Boolean indicating if operation exceeded threshold

## Monitoring

The system is monitored using Prometheus and Grafana. Key metrics include:
- Test execution latency
- Memory usage
- Error rates

Alert rules are configured via provisioning in the `provisioning/alerting` directory. For detailed information about monitoring and alerting, see [docs/monitoring.md](/Users/allan/Projects/iota/docs/monitoring.md).

## Configuration Validation Monitoring

IOTA includes a robust configuration validation monitoring system that tracks validation errors, warnings, and security issues in real-time.

### Metrics Collection

The system exports the following Prometheus metrics:
- `config_validation_errors`: Count of validation errors
- `config_validation_warnings`: Count of validation warnings
- `config_validation_security_issues`: Count of security-related issues
- `config_validation_duration_seconds`: Time taken for validation execution
- `config_validation_last_timestamp`: Unix timestamp of last validation

### Grafana Dashboard

A comprehensive Grafana dashboard is provided for monitoring:
1. Error trends and alerts
2. Warning patterns
3. Security issue detection
4. Validation performance
5. Last validation timestamp

To set up the dashboard:
```bash
# 1. Start the metrics exporter
python scripts/metrics_exporter.py

# 2. Configure Prometheus (prometheus.yml)
scrape_configs:
  - job_name: 'iota_validation'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 10s

# 3. Import the dashboard
# In Grafana UI:
# - Go to Dashboards > Import
# - Upload config/grafana/validation_dashboard.json
```

### Alert Rules

The dashboard includes pre-configured alerts for:
- High error rates (> 10 errors in 5min)
- Excessive warnings (> 20 warnings in 5min)
- Any security issues (immediate alert)
- Stale validations (> 15min since last run)

For detailed information, see [Configuration Validation Dashboard](/Users/allan/Projects/iota/config/grafana/README.md).

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
- [Redis Sentinel Setup](/Users/allan/Projects/iota/redis/README.md)
- [Docker Configuration](/Users/allan/Projects/iota/docker/README.md)

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
- [Monitoring Setup](/Users/allan/Projects/iota/monitoring/README.md)
- [Docker Configuration](/Users/allan/Projects/iota/docker/README.md)

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

### Documentation Tools

IOTA includes comprehensive documentation tooling to maintain high-quality documentation:

#### Validation

The documentation validator checks for common issues:

```bash
# Run documentation validation
python scripts/validate_docs.py

# Options:
#   --root-dir PATH    Root directory containing documentation files
```

The validator checks:
- Markdown syntax
- Internal links
- Code examples
- Cross-references
- Formatting consistency

#### Auto-fixing

The documentation fixer can automatically repair common issues:

```bash
# Show fixes without making changes
python scripts/fix_docs.py --dry-run

# Apply fixes
python scripts/fix_docs.py

# Options:
#   --root-dir PATH    Root directory containing documentation files
#   --dry-run         Show fixes without making changes
```

The fixer handles:
- Trailing whitespace
- Consecutive blank lines
- Common link patterns
- Markdown formatting

#### Pre-commit Hooks

Documentation validation is integrated into pre-commit hooks:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

For more information, see:
- [Documentation Style Guide](/Users/allan/Projects/iota/docs/style-guide.md)
- [Documentation Tooling ADR](/Users/allan/Projects/iota/docs/adr/0003-documentation-tooling.md)
- [Contributing Guidelines](/Users/allan/Projects/iota/CONTRIBUTING.md)
- [License](/Users/allan/Projects/iota/LICENSE)

## Documentation Changes

- [Monitoring Setup](/Users/allan/Projects/iota/docs/monitoring.md) - Learn about our monitoring infrastructure
- [Monitoring Changes (2025-02-22)](/Users/allan/Projects/iota/docs/monitoring_changes_2025_02_22.md) - Latest monitoring enhancements and performance metrics
- [Documentation Update (2025-02-22)](/Users/allan/Projects/iota/docs/documentation_update_2025_02_22.md) - Documentation structure improvements and tooling
- [Final Documentation Review (2025-02-22)](/Users/allan/Projects/iota/docs/final_documentation_review_2025_02_22.md) - Comprehensive review and next steps

## Version Management

IOTA uses semantic versioning for its validation schema to ensure consistent evolution of documentation templates. The version number (MAJOR.MINOR.PATCH) indicates:

- MAJOR: Breaking changes that require template updates
- MINOR: New features that maintain backward compatibility
- PATCH: Bug fixes that maintain backward compatibility

### Version Bump Utility

The `bump_version.py` script automates version management:

```bash
# Bump patch version (bug fixes)
./scripts/bump_version.py patch --changes "- Fixed validation for nested fields"

# Bump minor version (new features)
./scripts/bump_version.py minor --changes "- Added support for custom metadata fields"

# Bump major version (breaking changes)
./scripts/bump_version.py major --changes "- Restructured template format"
```

The utility automatically:
1. Updates the version in `validation_rules.json`
2. Updates `CHANGELOG.md` with provided changes
3. Validates the new configuration

### Version Compatibility

Template versions are checked for compatibility during validation:
- Templates with the same MAJOR version are compatible
- Higher MINOR versions are backward compatible
- PATCH versions only fix bugs and maintain compatibility

### Documentation

- [CHANGELOG.md](/Users/allan/Projects/iota/CHANGELOG.md): Detailed version history
- [Schema Versioning ADR](/Users/allan/Projects/iota/docs/adr/0002-schema-versioning.md): Version management decisions
- [Migration Guide](/Users/allan/Projects/iota/docs/migration-guide.md): Template update instructions

### Contributing

When contributing changes:

1. **Schema Changes**
   - Minor changes (backward compatible):
     - Add new optional fields
     - Extend existing validations
   - Major changes (breaking):
     - Remove/rename fields
     - Change validation rules
     - Modify template structure

2. **Version Updates**
   - Run version bump utility
   - Include clear changelog entry
   - Update documentation if needed

3. **Testing**
   - Run validation tests
   - Test with existing templates
   - Add tests for new features

### CI/CD Integration

The validation framework includes:
- Pre-commit hooks for version validation
- GitHub Actions for configuration checks
- Automated testing on PR/push

See [Contributing Guidelines](/Users/allan/Projects/iota/CONTRIBUTING.md) for detailed workflow.

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

## IOTA - Infrastructure Documentation and Template Management

A comprehensive solution for managing cloud infrastructure documentation and templates.

### Features

- Automated version management with semantic versioning
- Git hook integration for validation
- Changelog automation
- Comprehensive test suite
- Structured logging and error reporting

### Installation

```bash
# Clone the repository
git clone https://github.com/gdavis1361/iota.git
cd iota

# Install dependencies
pip install -r requirements.txt

# Install Git hooks
./scripts/install_git_hooks.sh
```

### Usage

#### Git Hooks

The pre-commit hook automatically validates your configuration and templates:

```bash
./scripts/install_git_hooks.sh
```

The hook will:
- Validate configuration files
- Verify template syntax
- Check version compatibility

#### Version Management

Bump version using semantic versioning:

```bash
python scripts/bump_version.py --type [major|minor|patch]
```

#### Changelog Generation

Generate or update changelog:

```bash
python scripts/update_changelog.py
```

#### Logging Configuration

The system uses structured logging with multiple levels:

```python
from server.core.logging_config import setup_logger

logger = setup_logger()
logger.info("Operation successful")
logger.error("Operation failed", extra={"error": str(err)})
```

### Testing

Run the test suite:

```bash
pytest tests/ -v
```

#### Test Coverage

```bash
pytest tests/ --cov=server --cov-report=html
```

### Troubleshooting

#### Common Issues

1. **Git Hook Installation Fails**
   - **Issue**: Hook not installed
   - **Solution**: Ensure you're running from project root and have proper permissions

2. **Invalid Version String**
   - **Issue**: Version parsing error
   - **Solution**: Use semantic versioning format (e.g., "1.0.0")

3. **Changelog Generation Fails**
   - **Issue**: Cannot update changelog
   - **Solution**: Ensure CHANGELOG.md exists and is writable

### Contributing

Please see [CONTRIBUTING.md](/Users/allan/Projects/iota/CONTRIBUTING.md) for guidelines.

### License

MIT License - see [LICENSE](/Users/allan/Projects/iota/LICENSE) for details.

## Documentation

### Documentation Tools

IOTA includes comprehensive documentation tooling to maintain high-quality documentation:

#### Validation

The documentation validator checks for common issues:

```bash
# Run documentation validation
python scripts/validate_docs.py

# Options:
#   --root-dir PATH    Root directory containing documentation files
```

The validator checks:
- Markdown syntax
- Internal links
- Code examples
- Cross-references
- Formatting consistency

#### Auto-fixing

The documentation fixer can automatically repair common issues:

```bash
# Show fixes without making changes
python scripts/fix_docs.py --dry-run

# Apply fixes
python scripts/fix_docs.py

# Options:
#   --root-dir PATH    Root directory containing documentation files
#   --dry-run         Show fixes without making changes
```

The fixer handles:
- Trailing whitespace
- Consecutive blank lines
- Common link patterns
- Markdown formatting

#### Pre-commit Hooks

Documentation validation is integrated into pre-commit hooks:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

For more information, see:
- [Documentation Style Guide](/Users/allan/Projects/iota/docs/style-guide.md)
- [Documentation Tooling ADR](/Users/allan/Projects/iota/docs/adr/0003-documentation-tooling.md)
- [Contributing Guidelines](/Users/allan/Projects/iota/CONTRIBUTING.md)
- [License](/Users/allan/Projects/iota/LICENSE)

### Monitoring Changes

- [Monitoring Setup](/Users/allan/Projects/iota/docs/monitoring.md) - Learn about our monitoring infrastructure
- [Monitoring Changes (2025-02-22)](/Users/allan/Projects/iota/docs/monitoring_changes_2025_02_22.md) - Latest monitoring enhancements and performance metrics
- [Final Documentation Review (2025-02-22)](/Users/allan/Projects/iota/docs/final_documentation_review_2025_02_22.md) - Comprehensive review and next steps
