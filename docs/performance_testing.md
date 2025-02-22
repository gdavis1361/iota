# Performance Testing Guide

## Overview

This guide outlines the performance testing procedures for IOTA, focusing on rate limiting, Redis operations, and configuration management.

## Test Scenarios

### 1. Rate Limiter Load Testing

#### Basic Load Test
```python
# Example using locust
from locust import HttpUser, task, between

class RateLimitUser(HttpUser):
    wait_time = between(0.1, 1.0)

    @task
    def test_endpoint(self):
        self.client.get("/api/test")
```

Test Parameters:
- Users: 100-1000 concurrent
- Ramp-up: 10 users/second
- Duration: 5 minutes
- Success Criteria:
  - 99th percentile latency < 100ms
  - Error rate < 0.1%

#### Redis Performance Metrics
Monitor:
- Operations/second
- Average response time
- Memory usage
- Connection pool status

### 2. Redis Clustering Configuration

#### Single Node Setup
```bash
# Example Redis configuration
maxmemory 2gb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60
```

#### Cluster Setup
```bash
# Example 3-node cluster
redis-cli --cluster create \
    127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
    --cluster-replicas 1
```

Performance Considerations:
- Memory allocation per node
- Network latency between nodes
- Replication lag monitoring
- Failover timing

### 3. Configuration Performance

Test scenarios for configuration loading:
- Cold start timing
- Configuration reload performance
- Environment variable validation speed
- Multiple concurrent configuration access

## Benchmarking Guidelines

### Key Metrics

1. Rate Limiter Performance
   - Requests/second handled
   - Time to process rate limit check
   - Redis operation latency
   - Memory usage per active key

2. Configuration Performance
   - Time to load configuration
   - Memory usage per configuration instance
   - Validation time for environment variables

### Benchmark Tools

1. Redis Benchmarking
```bash
redis-benchmark -n 100000 -c 50 -P 16 -t set,get
```

2. Application Benchmarking
```python
import time
from server.core.config import create_settings
from server.app.core.rate_limiter import RateLimiter

def benchmark_rate_limiter():
    settings = create_settings()
    limiter = RateLimiter(settings.rate_limit_config, redis_client)

    start = time.perf_counter()
    for _ in range(10000):
        limiter.check_rate_limit("test-user")
    end = time.perf_counter()

    return end - start
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Performance Tests
on: [push, pull_request]

jobs:
  perf-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run performance tests
        run: python -m pytest tests/performance/
      - name: Run Redis benchmarks
        run: redis-benchmark -n 100000
```

### Performance Regression Detection

1. Store benchmark results:
```python
def save_benchmark(results: dict):
    with open("benchmark_results.json", "a") as f:
        json.dump({
            "timestamp": time.time(),
            "git_commit": os.getenv("GITHUB_SHA"),
            "results": results
        }, f)
```

2. Compare with baseline:
```python
def check_regression(current_results: dict, baseline: dict):
    max_regression = 0.1  # 10% degradation threshold

    for metric, value in current_results.items():
        if value > baseline[metric] * (1 + max_regression):
            raise PerformanceRegression(f"{metric} degraded by {value/baseline[metric]}")
```

## Alert Rules

### Redis Alerts
- CPU usage > 80% for 5 minutes
- Memory usage > 90%
- Replication lag > 10 seconds
- Connection count > 80% of max_connections

### Application Alerts
- Rate limit check latency > 10ms
- Configuration load time > 100ms
- Error rate > 1%
- Request queue length > 1000

## Best Practices

1. Regular Performance Testing
   - Run full suite weekly
   - Basic checks on every PR
   - Detailed analysis monthly

2. Resource Management
   - Clear Redis keys regularly
   - Monitor memory usage
   - Use connection pooling
   - Implement proper timeouts

3. Test Data Management
   - Use realistic data volumes
   - Clean up test data
   - Simulate real traffic patterns
   - Test edge cases

## Troubleshooting Guide

Common Issues:
1. High Redis Latency
   - Check network connectivity
   - Monitor memory usage
   - Review key expiration settings
   - Analyze slow log

2. Rate Limiter Performance
   - Check Redis connection pool
   - Monitor key count
   - Review cleanup timing
   - Analyze request patterns

3. Configuration Performance
   - Check environment variable count
   - Monitor validation timing
   - Review caching strategy
   - Analyze startup time

## Future Considerations

1. Scalability
   - Redis cluster expansion
   - Multiple rate limiter instances
   - Configuration distribution
   - Load balancing

2. Monitoring
   - Distributed tracing
   - Detailed metrics
   - Performance dashboards
   - Automated analysis

3. Optimization
   - Key compression
   - Batch operations
   - Cache optimization
   - Connection management
