# IOTA Rate Limiter Operations Runbook

## Overview
This runbook provides operational procedures for monitoring, maintaining, and troubleshooting the IOTA rate limiting system.

## Monitoring Components

### Metrics Endpoint
- **Location**: `/metrics`
- **Format**: Prometheus exposition format
- **Scrape Interval**: 15s (recommended)
- **Retention**: 15 days (recommended)

### Key Metrics

#### Rate Limit Metrics
- `rate_limit_exceeded_total{endpoint=""}` - Total rate limit violations
- `failed_login_attempts_total{ip=""}` - Failed login attempts
- `rate_limit_remaining{endpoint=""}` - Remaining requests in window
- `rate_limit_window_reset_seconds{endpoint=""}` - Time until window reset
- `rate_limit_check_duration_seconds` - Request processing latency

#### Redis Metrics
- `redis_connection_errors_total` - Redis connection failures
- `redis_memory_used_bytes` - Redis memory usage

## Alert Rules

### Critical Alerts

#### CriticalRateLimitViolations
- **Threshold**: >500 violations/hour
- **Duration**: 15m
- **Action**: 
  1. Check `/var/log/iota/rate_limit.log` for violation patterns
  2. Verify if legitimate traffic or potential attack
  3. If attack, enable additional security measures
  4. If legitimate, consider adjusting limits

#### RedisConnectionIssues
- **Threshold**: Any connection error
- **Duration**: 1m
- **Action**:
  1. Check Redis server status
  2. Verify network connectivity
  3. Check Redis logs
  4. Restart Redis if necessary

#### AuthEndpointOverload
- **Threshold**: >10 violations/15m on auth endpoint
- **Duration**: 5m
- **Action**:
  1. Review auth logs for suspicious patterns
  2. Check for credential stuffing attacks
  3. Enable additional auth protection if needed

### Warning Alerts

#### HighRateLimitViolations
- **Threshold**: >100 violations/hour
- **Duration**: 5m
- **Action**: Monitor for escalation to critical

#### RateLimitLatencyHigh
- **Threshold**: 95th percentile >100ms
- **Duration**: 5m
- **Action**: 
  1. Check Redis CPU usage
  2. Review request patterns
  3. Consider Redis optimization

#### LowRateLimitCapacity
- **Threshold**: <10% capacity remaining
- **Duration**: 15m
- **Action**: Plan capacity increase if trend continues

## Maintenance Procedures

### Rate Limit Cleanup Script
- **Location**: `/scripts/cleanup_rate_limits.py`
- **Schedule**: Run daily during low traffic
- **Usage**:
```bash
# Dry run first
./cleanup_rate_limits.py --dry-run

# If safe, run cleanup
./cleanup_rate_limits.py
```

### Window Compression
- **Frequency**: Automatic during cleanup
- **Monitoring**: Check Redis memory usage trend
- **Threshold**: Alert if memory usage >80%

### Metric Aggregation
- **Frequency**: Automatic during cleanup
- **Location**: `/var/lib/prometheus/rate_limit_aggregated.prom`
- **Retention**: 30 days

## Troubleshooting Guide

### High Rate of Violations
1. Check logs for patterns
2. Identify top violating IPs/endpoints
3. Review recent changes
4. Consider temporary limit adjustments

### Redis Issues
1. Check Redis memory usage
2. Verify connection settings
3. Review cleanup script logs
4. Check for network issues

### Performance Problems
1. Monitor request latency
2. Check Redis CPU usage
3. Review connection pool settings
4. Verify proper indexing

## Scaling Considerations

### Redis Memory
- Monitor memory usage
- Set maxmemory-policy to volatile-ttl
- Consider Redis cluster if needed

### Alert Thresholds
- Review and adjust based on traffic
- Consider time-of-day patterns
- Adjust for known peak periods

### Cleanup Schedule
- Adjust frequency based on data growth
- Monitor cleanup duration
- Optimize for low-traffic periods

## Emergency Procedures

### Rate Limit Bypass
In case of emergency requiring temporary rate limit bypass:

1. Document the reason
2. Get approval from security team
3. Adjust limits temporarily
4. Monitor closely
5. Reset after incident

### Redis Failure
If Redis becomes unavailable:

1. System will fail-open (configurable)
2. Check Redis logs
3. Verify disk space
4. Check network connectivity
5. Restore from backup if needed

## Backup and Recovery

### Redis Backup
- Frequency: Daily
- Retention: 7 days
- Location: `/var/backup/redis/`
- Verify backups weekly

### Configuration Backup
- Store in version control
- Include alert rules
- Include dashboard configurations
- Document all changes

## Contact Information

### On-Call Support
- Primary: DevOps Team
- Secondary: Security Team
- Escalation: Platform Team

### External Support
- Redis Support: [contact info]
- Prometheus Support: [contact info]
- Security Team: [contact info]
