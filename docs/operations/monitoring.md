# Operations Monitoring Guide

## Overview
This guide details the monitoring setup, metrics collection, and operational procedures for the IOTA project.

## Monitoring Stack

### 1. Core Components
- Prometheus: Metrics collection
- Grafana: Visualization
- AlertManager: Alert management
- Node Exporter: System metrics
- Blackbox Exporter: External monitoring

### 2. Custom Exporters
- Application metrics
- Business metrics
- Performance metrics
- Error tracking

## Metrics Collection

### 1. System Metrics
```yaml
# prometheus/node-exporter.yml
scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### 2. Application Metrics
```python
from prometheus_client import Counter, Histogram, Summary

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Response time
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Business metrics
BUSINESS_OPERATIONS = Counter(
    'business_operations_total',
    'Total business operations',
    ['operation_type', 'status']
)
```

## Dashboards

### 1. System Dashboard
- CPU utilization
- Memory usage
- Disk I/O
- Network traffic

### 2. Application Dashboard
- Request rate
- Error rate
- Response times
- Active users

### 3. Business Dashboard
- Transaction volume
- Success rates
- User activity
- Feature usage

## Alert Rules

### 1. System Alerts
```yaml
# prometheus/alerts/system.yml
groups:
  - name: system
    rules:
      - alert: HighCPUUsage
        expr: avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High CPU usage detected
```

### 2. Application Alerts
```yaml
# prometheus/alerts/application.yml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
```

## Logging

### 1. Log Collection
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "request_processed",
    method="POST",
    endpoint="/api/v1/data",
    duration_ms=150,
    status_code=200
)
```

### 2. Log Aggregation
- ELK Stack configuration
- Log retention policies
- Search and analysis

## Performance Monitoring

### 1. Response Time Tracking
```python
@app.middleware("http")
async def add_response_timing(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

### 2. Resource Usage
- Memory profiling
- CPU profiling
- Database connection tracking
- Cache hit rates

## Health Checks

### 1. Application Health
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": await check_database(),
        "cache": await check_cache()
    }
```

### 2. Dependencies Health
- Database connectivity
- Redis status
- External services
- Network status

## Incident Response

### 1. Alert Response
1. Acknowledge alert
2. Assess severity
3. Follow runbook
4. Update status
5. Post-mortem

### 2. Runbooks
- Service restart procedures
- Backup restoration
- Scaling procedures
- Emergency contacts

## Maintenance

### 1. Backup Verification
```bash
# Verify backup integrity
python scripts/verify_backup.py

# Test restoration
python scripts/test_restore.py --backup-id latest
```

### 2. Monitoring Maintenance
- Update alert thresholds
- Review dashboard effectiveness
- Adjust retention periods
- Update runbooks

## Related Documentation
- [Development Guide](/Users/allan/Projects/iota/docs/operations/../development.md)
- [Performance Testing](/Users/allan/Projects/iota/docs/operations/../../tests/performance/README.md)
- [Integration Testing](/Users/allan/Projects/iota/docs/operations/../../tests/integration/README.md)
- [Alerts Guide](/Users/allan/Projects/iota/docs/operations/alerts.md)
