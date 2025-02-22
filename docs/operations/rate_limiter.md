# IOTA Rate Limiter Operations Guide

## Overview

The IOTA Rate Limiter provides distributed rate limiting using Redis, with comprehensive monitoring via Prometheus and Sentry. This guide covers operational aspects including monitoring, alerting, and troubleshooting.

## Monitoring Setup

### Available Metrics

#### Rate Limit Metrics
- `rate_limit_exceeded_total{endpoint="", ip=""}`
  - Type: Counter
  - Description: Number of rate limit violations
  - Labels:
    - `endpoint`: API endpoint path
    - `ip`: Client IP address
  - Alert Threshold: >100/hour indicates potential abuse

- `rate_limit_remaining{endpoint="", ip=""}`
  - Type: Gauge
  - Description: Remaining requests in current window
  - Labels: Same as above
  - Alert Threshold: <10% capacity for >15 minutes

- `rate_limit_window_reset_seconds{endpoint="", ip=""}`
  - Type: Gauge
  - Description: Seconds until window reset
  - Use: Track window lifecycle

- `failed_login_attempts_total{ip=""}`
  - Type: Counter
  - Description: Failed login attempts
  - Alert Threshold: >5 attempts/15 minutes

- `rate_limit_check_duration_seconds{endpoint=""}`
  - Type: Histogram
  - Description: Rate limit check latency
  - Alert Threshold: p95 >100ms

### Grafana Dashboard Setup

1. Import the provided dashboard template:
   ```
   Dashboard ID: iota_rate_limiter_v1
   ```

2. Configure the following panels:

#### Rate Limit Overview
```promql
# Rate limit violations per minute
rate(rate_limit_exceeded_total[1m])

# Failed login attempts
rate(failed_login_attempts_total[5m])

# Remaining capacity by endpoint
rate_limit_remaining
```

#### Performance Metrics
```promql
# Rate limit check latency
histogram_quantile(0.95,
  rate(rate_limit_check_duration_seconds_bucket[5m]))

# Request rate by endpoint
rate(rate_limit_remaining[1m])
```

#### Top Violators
```promql
# Top IPs by rate limit violations
topk(10, rate(rate_limit_exceeded_total[1h]))
```

## Alert Rules

### Prometheus Alert Rules
```yaml
groups:
- name: rate_limiter
  rules:
  - alert: HighRateLimitViolations
    expr: rate(rate_limit_exceeded_total[1h]) > 100
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High rate limit violations
      description: "{{ $value }} violations/hour for {{ $labels.endpoint }}"

  - alert: HighFailedLogins
    expr: rate(failed_login_attempts_total[15m]) > 5
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: High failed login attempts
      description: "{{ $value }} failed attempts from {{ $labels.ip }}"

  - alert: RateLimitLatencyHigh
    expr: histogram_quantile(0.95, rate(rate_limit_check_duration_seconds_bucket[5m])) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: Rate limit checks are slow
      description: "95th percentile latency is {{ $value }}s"
```

## Operational Procedures

### Daily Checks
1. Monitor rate limit violation trends
2. Review failed login patterns
3. Check Redis memory usage
4. Verify metric collection

### Weekly Tasks
1. Review alert thresholds
2. Clean up expired metrics
3. Analyze violation patterns
4. Update IP allowlists/blocklists

### Monthly Tasks
1. Review and update rate limits
2. Analyze traffic patterns
3. Optimize Redis configuration
4. Update documentation

## Troubleshooting Guide

### High Rate Limit Violations
1. Check logs for patterns
2. Review client IPs
3. Verify rate limit configuration
4. Consider updating limits

### Redis Issues
1. Check Redis memory usage
2. Verify connection settings
3. Review key expiration
4. Monitor sorted set size

### Metric Collection Issues
1. Verify Prometheus endpoint
2. Check metric cardinality
3. Review storage usage
4. Validate alert rules

### Performance Issues
1. Monitor Redis latency
2. Check rate limit check duration
3. Review middleware overhead
4. Verify Redis pipelining

## Scaling Considerations

### Redis Scaling
- Monitor memory usage
- Consider Redis cluster
- Implement key expiration
- Use appropriate persistence

### Metric Scaling
- Implement metric aggregation
- Monitor cardinality
- Set retention policies
- Consider remote storage

## Maintenance Tasks

### Metric Cleanup
```python
# Example cleanup script
from redis import Redis
import time

def cleanup_expired_metrics(redis_client):
    """Clean up expired rate limit metrics"""
    now = time.time()
    pattern = "rate_limit:*"

    # Scan for expired keys
    for key in redis_client.scan_iter(pattern):
        # Check if window has expired
        if redis_client.zcount(key, float('-inf'), now) == 0:
            redis_client.delete(key)
```

## Configuration Updates

### Rate Limit Updates
```python
# Example configuration update
app.add_middleware(
    RateLimitMiddleware,
    endpoint_limits={
        "/api/v1/auth/token": {
            "window": 900,  # 15 minutes
            "max_requests": 5
        }
    }
)
```

### Alert Threshold Updates
```yaml
# prometheus/alerts.yml
- alert: HighRateLimitViolations
  expr: rate(rate_limit_exceeded_total[1h]) > new_threshold
```

## Best Practices

### Monitoring Best Practices
- Keep metric cardinality under control
- Use appropriate time windows
- Monitor Redis memory usage
- Review alert thresholds regularly

### Performance Best Practices
- Use Redis pipelining
- Implement metric aggregation
- Clean up expired metrics
- Monitor latency trends

### Security Best Practices
- Protect metrics endpoint
- Monitor failed logins
- Review IP patterns
- Update rate limits based on usage

### Documentation Best Practices
- Keep runbooks updated
- Document configuration changes
- Maintain troubleshooting guides
- Update dashboard documentation

## Rate Limiting Configuration

### Algorithm Configuration
#### Rate Limit Algorithm
- Description: Leaky Bucket Algorithm
- Parameters:
  - `window`: Time window for rate limiting (seconds)
  - `max_requests`: Maximum requests allowed in time window

### Redis Configuration
#### Redis Connection Settings
- Host: `localhost`
- Port: `6379`
- Database: `0`

### Monitoring and Alerts
#### Prometheus Configuration
- Scrape interval: `1m`
- Evaluation interval: `1m`
