# Observability Guide

## Overview

IOTA uses OpenTelemetry for distributed tracing and Prometheus/Grafana for metrics collection and visualization. This guide explains how to configure and use these observability tools.

## OpenTelemetry Configuration

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize OpenTelemetry in your application:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Set up tracer
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

### Sampling Configuration

#### Development
```python
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler

# Sample all traces
provider = TracerProvider(sampler=AlwaysOnSampler())
```

#### Production
```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

# Sample 10% of traces
provider = TracerProvider(
    sampler=ParentBasedTraceIdRatio(0.1)
)
```

### Key Trace Points

1. Rate Limiter Operations:
   - `check_rate_limit`: Root span for rate limit checks
   - `redis_ping`: Redis connection verification
   - `redis_operations`: Redis key operations

Example trace attributes:
```python
span.set_attribute("identifier", identifier)
span.set_attribute("window", window)
span.set_attribute("max_requests", max_requests)
span.set_attribute("current_count", current)
span.set_attribute("ttl", ttl)
```

## Metrics Collection

### Prometheus Configuration

1. Create prometheus.yml:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'iota'
    static_configs:
      - targets: ['localhost:8000']
```

2. Key Metrics:
   - `rate_limit_requests`: Counter of rate limit checks
   - `rate_limit_duration`: Histogram of check durations
   - `redis_errors`: Counter of Redis errors

### Metric Labels

```python
# Request counter with status label
rate_limit_counter.add(1, {"limited": str(is_limited)})

# Duration histogram
rate_limit_duration.record(duration)

# Error counter
redis_error_counter.add(1)
```

## Grafana Dashboard

### Installation

1. Import dashboard:
   - Open Grafana
   - Click "+" > "Import"
   - Upload `monitoring/grafana/rate_limiter_dashboard.json`

### Dashboard Panels

1. Rate Limit Requests:
   - Shows rate of requests over time
   - Grouped by limited/allowed status
   - Query: `rate(rate_limit_requests_total{limited="true"}[5m])`

2. Rate Limit Duration:
   - Shows average operation duration
   - Alert threshold: > 1ms
   - Query: `rate(rate_limit_duration_sum[5m]) / rate(rate_limit_duration_count[5m])`

3. Redis Errors:
   - Shows error rate over time
   - Alert threshold: > 0
   - Query: `rate(redis_errors_total[5m])`

### Alert Rules

1. Rate Limit Duration Alert:
```yaml
alert: HighRateLimitLatency
expr: rate(rate_limit_duration_sum[5m]) / rate(rate_limit_duration_count[5m]) > 0.001
for: 5m
labels:
  severity: warning
annotations:
  summary: High rate limit check latency
  description: Rate limit checks taking longer than 1ms on average
```

2. Redis Error Alert:
```yaml
alert: RedisErrors
expr: rate(redis_errors_total[5m]) > 0
for: 1m
labels:
  severity: critical
annotations:
  summary: Redis errors detected
  description: Rate limiter encountering Redis errors
```

## Alert Routing and Notifications

### Configuration

Alerts are routed based on severity:
- Critical alerts -> PagerDuty (1h repeat interval)
- Warning alerts -> Slack (#iota-alerts channel)

### Environment Variables

Required for alert routing:
```bash
SLACK_API_URL=https://hooks.slack.com/services/xxx/yyy/zzz
PAGERDUTY_ROUTING_KEY=your-pagerduty-key
```

### Alert Groups

Alerts are grouped by:
- Alert name
- Severity level
- Component/service

This reduces noise while maintaining visibility of related issues.

### Response Procedures

1. Critical Alerts (PagerDuty)
   - Immediate response required (< 15 minutes)
   - Follow incident response playbook
   - Update status in #incidents channel

2. Warning Alerts (Slack)
   - Review within 1 business hour
   - Update thread with investigation status
   - Create ticket if persistent issue

### Runbooks

Each alert includes a runbook URL with:
- Detailed alert description
- Common causes
- Investigation steps
- Resolution procedures

## Production Guidelines

### Sampling Strategy

1. Start with 10% sampling rate
2. Adjust based on:
   - Traffic volume
   - Storage capacity
   - Analysis needs

### Resource Requirements

1. OpenTelemetry:
   - Memory: ~50MB base
   - CPU: < 1% overhead
   - Network: ~100KB/s per 1000 requests

2. Prometheus:
   - Storage: ~1MB/day per time series
   - Memory: ~500MB base
   - CPU: < 0.1 core

### Retention Policies

1. Traces:
   - Hot storage: 7 days
   - Cold storage: 30 days

2. Metrics:
   - High resolution: 7 days
   - Downsampled: 90 days

## Troubleshooting

### Common Issues

1. Missing Traces:
   - Check sampling rate
   - Verify exporter configuration
   - Check network connectivity

2. High Latency:
   - Review batch size configuration
   - Check export interval
   - Monitor resource usage

3. Missing Metrics:
   - Verify Prometheus scrape config
   - Check target health
   - Review firewall rules

## Best Practices

1. Tracing:
   - Use semantic conventions
   - Add business context
   - Handle errors properly

2. Metrics:
   - Use appropriate metric types
   - Add relevant labels
   - Keep cardinality manageable

3. Alerting:
   - Define clear thresholds
   - Avoid alert fatigue
   - Include actionable information
