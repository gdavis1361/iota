# IOTA Performance Testing Framework

## Overview
This directory contains the IOTA performance testing and monitoring framework, designed to run comprehensive benchmarks and system health checks across different platforms.

## Scripts

### benchmark_performance.sh
Performance benchmarking script that tests system behavior under various data loads.

#### Features
- Non-blocking I/O operations
- Cross-platform support (Linux & macOS)
- Comprehensive resource monitoring
- Automatic process cleanup
- Dataset size testing (100, 1000, 5000 records)

#### Requirements
- bash 4.0+
- System utilities:
  - Linux: `free`, `top`, `df`
  - macOS: `vm_stat`, `top`, `df`, `pagesize`

#### Platform-Specific Notes

##### macOS
Memory reporting uses the following calculation:
```bash
# Memory calculation
page_size=$(pagesize)
total = (free + active + inactive + speculative + wired) * page_size
used = (active + wired) * page_size
usage_percent = (used/total) * 100
```

##### Linux
Memory reporting uses the standard `free` command output:
```bash
free -m | awk '/Mem:/ {printf "Memory: %.2f MB\n", $3}'
```

### Resource Monitoring
The framework tracks:
- Memory usage (MB and percentage)
- CPU utilization (percentage)
- Disk usage (percentage)
- Process count
- Test completion times

### Error Handling
- Automatic cleanup of temporary files
- Process management with PID tracking
- Graceful termination of child processes
- Platform-specific command fallbacks

## Usage

```bash
# Run benchmark tests
./benchmark_performance.sh

# Default test sizes: 100, 1000, 5000 records
# Timeout: 300 seconds
```

### Output Format
```
=== IOTA Performance Benchmark (Non-blocking) ===
Date: YYYY-MM-DDTHH:mm:ssZ
Test sizes: 100 1000 5000
Timeout: 300s

=== Trend Analysis Performance ===
Dataset size: N records
...
Memory: XX.XX MB (YY.Y% used)
CPU: ZZ.Z%
Disk: WW%
```

## Rate Limiting

### Overview
The IOTA framework includes a Redis-based rate limiter that provides:
- Global rate limiting across all endpoints
- Endpoint-specific rate limiting
- Failed login attempt tracking
- Configurable time windows and request limits
- Standard rate limit headers

### Configuration
The rate limiter uses Redis for persistent storage and can be configured with:
- Default time window (in seconds)
- Default maximum requests per window
- Redis connection parameters

### Rate Limit Headers
The following headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed in the window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Seconds until the current window resets

### Redis Key Format
Rate limit keys follow this format:
```
rate_limit:<ip>[:endpoint]
```
Example keys:
- Global limit: `rate_limit:127.0.0.1`
- API endpoint: `rate_limit:127.0.0.1:api`
- Failed logins: `rate_limit:127.0.0.1:login_attempts`

### Error Handling
- Redis connection failures: Fail open to allow requests
- Invalid configurations: Use default values
- Cleanup: Automatic removal of expired entries

### Monitoring
Monitor these metrics for rate limiting health:
- Redis connection status
- Rate limit violations per endpoint
- Failed login attempts
- Redis memory usage
- Key cleanup performance

### Example Usage
```python
from rate_limiter import RateLimiter

# Initialize rate limiter
limiter = RateLimiter(
    redis_host='localhost',
    redis_port=6379,
    default_window=60,  # 1 minute
    default_max_requests=100
)

# Check rate limit for an IP
allowed, wait_time, headers = limiter.check_rate_limit('127.0.0.1')
if not allowed:
    print(f"Rate limit exceeded. Try again in {wait_time} seconds")
    # Return 429 Too Many Requests with headers

# Check endpoint-specific limit
allowed, wait_time, headers = limiter.check_rate_limit(
    '127.0.0.1',
    endpoint='api',
    window=300,  # 5 minutes
    max_requests=1000
)

# Track failed login
allowed, wait_time, headers = limiter.record_failed_login(
    '127.0.0.1',
    window=900,  # 15 minutes
    max_attempts=5
)
```

### Best Practices
1. Use endpoint-specific limits for different resource types
2. Set shorter windows for sensitive endpoints
3. Monitor rate limit violations
4. Configure appropriate Redis persistence
5. Regularly clean up expired entries

### Troubleshooting
1. Check Redis connection and persistence settings
2. Verify rate limit configuration values
3. Monitor Redis memory usage
4. Review rate limit violation logs
5. Check key expiration settings

## Future Enhancements
- Trend analysis visualization
- Long-term metric storage
- Configurable alert thresholds
- Progress tracking for large datasets
- BSD platform support

## Troubleshooting
If you encounter issues:
1. Ensure all required system utilities are available
2. Check file permissions (scripts should be executable)
3. Verify bash version (`bash --version`)
4. Check system resource availability
5. Review temporary directory permissions
