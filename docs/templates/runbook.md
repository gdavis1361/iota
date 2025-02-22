# Operational Runbook Template

## Service Overview

### Purpose
[Describe the primary purpose and business value of this service]

### Architecture
High-level description of the service architecture.

### Dependencies
- Upstream Services:
  - [Service 1]: [Description]
  - [Service 2]: [Description]
- Downstream Services:
  - [Service 1]: [Description]
  - [Service 2]: [Description]
- External Dependencies:
  - [Dependency 1]: [Description]
  - [Dependency 2]: [Description]

### Service Level Objectives (SLOs)
- Availability Target: [e.g., 99.9%]
- Latency Target: [e.g., p95 < 200ms]
- Error Rate Target: [e.g., < 0.1%]

## Monitoring

### Key Metrics
| Metric | Description | Normal Range | Alert Threshold |
|--------|-------------|--------------|-----------------|
| Metric1 | Description | Range | Threshold |

### Dashboards
- Dashboard 1: [link and description]
- Dashboard 2: [link and description]

### Alerts
| Alert Name | Trigger Condition | Severity | Response Time |
|------------|------------------|-----------|---------------|
| Alert1 | Condition | Severity | Time |

## IOTA Runbook

### Checking System Performance

1. View aggregated metrics for an operation:
```python
from typing import Dict, Any
from datetime import datetime, timedelta
from server.core.monitoring import PerformanceMonitor

# Initialize monitor
monitor = PerformanceMonitor()

# Get metrics for the last hour
start_time = datetime.utcnow() - timedelta(hours=1)
metrics: Dict[str, Any] = monitor.get_metrics(
    operation="user_login",
    start_time=start_time
)

print(f"Error Rate: {metrics['error_rate']:.2%}")
print(f"P95 Latency: {metrics['p95_latency_ms']}ms")
print(f"Success Rate: {metrics['success_rate']:.2%}")
```

2. Check system health:
```python
from typing import Dict, Any
from server.core.health import HealthCheck

# Initialize health checker
health = HealthCheck()

# Run full health check
status: Dict[str, Any] = health.check_all()

if status["healthy"]:
    print("All systems operational")
    print(f"Database Latency: {status['database_latency_ms']}ms")
    print(f"Redis Latency: {status['redis_latency_ms']}ms")
else:
    print("System issues detected:")
    for service, details in status["services"].items():
        if not details["healthy"]:
            print(f"- {service}: {details['error']}")
```

### Common Issues

1. High Error Rates
   - **Symptom**: Error rate exceeds threshold (default 10%)
   - **Check**: Review metrics for specific operation types
   - **Resolution**:
     * Check logs for error details
     * Verify external service connectivity
     * Check resource utilization

2. Slow Operations
   - **Symptom**: Operations marked as slow (exceeding threshold)
   - **Check**: Query metrics for duration patterns
   - **Resolution**:
     * Review operation implementation
     * Check for resource contention
     * Consider optimization opportunities

3. Database Growth
   - **Symptom**: Metrics database size growing too large
   - **Check**: Monitor database file size
   - **Resolution**:
     * Run cleanup for old metrics:
       ```python
       monitor.cleanup_old_metrics()
       ```
     * Adjust sampling window if needed

### Maintenance Tasks

1. Regular Cleanup
   ```python
   # Clean up metrics older than default window (1 hour)
   monitor.cleanup_old_metrics()

   # Clean up metrics older than specific window
   monitor.cleanup_old_metrics(window_seconds=86400)  # 24 hours
   ```

2. Database Optimization
   ```sql
   -- Optimize SQLite database
   VACUUM;
   ANALYZE;
   ```

3. Configuration Updates
   - Review and adjust thresholds in `server/core/config/base.py`:
     * `SLOW_REQUEST_THRESHOLD_MS`
     * `SAMPLING_WINDOW_SECONDS`
     * `ERROR_RATE_THRESHOLD`

## Incident Response

### Severity Levels
| Level | Description | Example | Response Time |
|-------|-------------|---------|---------------|
| P1 | Critical | Service Down | Immediate |
| P2 | High | Degraded | 30 mins |
| P3 | Medium | Minor Impact | 2 hours |
| P4 | Low | Cosmetic | 24 hours |

### Initial Assessment
1. Check dashboard [link]
2. Review recent alerts
3. Check dependent services

### Common Issues

#### Issue: [Problem Name]
**Symptoms:**
- Symptom 1
- Symptom 2

**Diagnosis:**
```bash
# Commands to diagnose the issue
command argument1 argument2
```

**Resolution:**
1. Step 1
2. Step 2

**Verification:**
```bash
# Commands to verify resolution
verify_command argument1
```

## Routine Operations

### Daily Checks
- [ ] Check 1: [Description]
- [ ] Check 2: [Description]

### Weekly Tasks
- [ ] Task 1: [Description]
- [ ] Task 2: [Description]

### Monthly Tasks
- [ ] Task 1: [Description]
- [ ] Task 2: [Description]

## Backup and Recovery

### Backup Procedures
1. Step 1: [Description]
2. Step 2: [Description]

### Recovery Procedures
1. Step 1: [Description]
2. Step 2: [Description]

### Data Retention
- Policy: [Description]
- Retention Period: [Duration]
- Archival Process: [Description]

## Security

### Access Control
- Required Permissions:
  - Permission 1: [Description]
  - Permission 2: [Description]
- Authentication Methods:
  - Method 1: [Description]
  - Method 2: [Description]
- Authorization Levels:
  - Level 1: [Description]
  - Level 2: [Description]

### Security Protocols
1. Protocol 1: [Description]
2. Protocol 2: [Description]

### Compliance Requirements
- Requirement 1: [Description]
- Requirement 2: [Description]

## Maintenance

### Scheduled Maintenance
- Windows: [Time/Day]
- Approvals: [Process]
- Communication: [Plan]

### Change Management
- Process: [Description]
- Testing: [Requirements]
- Rollback: [Procedures]

## Support

### Escalation Path
1. Level 1: [Contact Info]
2. Level 2: [Contact Info]
3. Level 3: [Contact Info]

### External Contacts
- Vendor Support: [Contact Info]
- Third-party Services: [Contact Info]
- Emergency Contacts: [Contact Info]

## References

### Documentation
- Link 1: [Description]
- Link 2: [Description]

### Tools
- Tool 1: [Link and Purpose]
- Tool 2: [Link and Purpose]

## Changelog

| Date | Version | Description |
|------|---------|-------------|
| YYYY-MM-DD | v1.0.0 | Initial version |
