# Alert Routing Strategy

## Status
Accepted

## Context
As we implement comprehensive monitoring for the IOTA system, we need a clear strategy for routing different types of alerts to appropriate channels and teams. This ensures that critical issues receive immediate attention while preventing alert fatigue.

## Decision

We will implement a two-tier alert routing strategy:

### 1. Critical Alerts (PagerDuty)
- **Response Time:** < 15 minutes
- **Criteria:**
  - Service availability impacts
  - Data loss risks
  - Security incidents
  - Performance degradation > 20%
  - **System Thresholds:**
    - Latency > 2ms (P95)
    - Memory Usage > 1GB
    - Any Redis Errors
    - Rejection Rate > 20%
- **Routing:**
  - Primary: PagerDuty on-call rotation
  - Secondary: Slack #incidents channel
- **Repeat Interval:** 1 hour
- **Auto-resolution:** 24 hours

### 2. Warning Alerts (Slack)
- **Response Time:** < 1 business hour
- **Criteria:**
  - Performance degradation < 20%
  - Resource usage warnings
  - Non-critical errors
  - Configuration issues
  - **System Thresholds:**
    - Latency > 1ms (P95)
    - Memory Usage > 750MB
    - Redis Error Rate > 0 but < 1/min
    - Rejection Rate > 10% but < 20%
- **Routing:**
  - Primary: Slack #iota-alerts channel
  - Secondary: Ticket creation if persistent
- **Repeat Interval:** 4 hours
- **Auto-resolution:** 7 days

### Alert Grouping
- Group by: alert name, severity, service
- Wait period: 30s for aggregation
- Group interval: 5m between updates

### Metric Collection
- Collection interval: 5m
- Query timeout: 30s
- Retention period: 30 days
- Data resolution: 1m for last 24h, 5m for older data

## Consequences

### Positive
- Clear escalation paths
- Reduced alert noise
- Appropriate urgency levels
- Documented response procedures
- Quantifiable thresholds for automated response

### Negative
- Requires regular threshold review
- May need adjustment based on load patterns
- Additional monitoring overhead

### Risks
- Alert fatigue if thresholds incorrect
- Missed critical issues if miscategorized
- External service reliability impact

## Implementation Notes

### Performance Report Generation
- Reports generated every 5 minutes
- Uses Prometheus for metric collection
- Implements error handling and fallbacks
- Provides formatted output with unit conversions

### Monitoring Coverage
1. **Rate Limiter Performance**
   - Requests per second
   - Rejection rates
   - Average latency
   - Error counts

2. **System Health**
   - Memory usage
   - Redis errors
   - Service availability
   - Response times

3. **Threshold Violations**
   - Latency breaches
   - Memory limits
   - Error rates
   - Rejection spikes

### Configuration Management
   - Store API keys in secrets management
   - Version control alert rules
   - Document threshold adjustments

### Documentation
   - Maintain runbooks
   - Update response procedures
   - Track resolution patterns

## Review Schedule
- Thresholds: Monthly review
- Alert patterns: Quarterly analysis
- False positive rate: Weekly review
- Documentation: Bi-weekly updates

## Alternatives Considered

### Single Channel Strategy
- All alerts to Slack
- Rejected: No urgency differentiation

### Email-based Alerts
- Email notifications
- Rejected: Poor real-time response

### Custom Alert Manager
- In-house solution
- Rejected: Maintenance overhead
