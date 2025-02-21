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
- **Routing:**
  - Primary: Slack #iota-alerts channel
  - Secondary: Ticket creation if persistent
- **Repeat Interval:** 4 hours
- **Auto-resolution:** 7 days

### Alert Grouping
- Group by: alert name, severity
- Wait period: 30s for aggregation
- Group interval: 5m between updates

## Consequences

### Positive
- Clear escalation paths
- Reduced alert noise
- Appropriate urgency levels
- Documented response procedures

### Negative
- Additional configuration complexity
- New external service dependencies
- Training requirements
- Potential for missed alerts during grouping

### Risks
- Alert fatigue if thresholds incorrect
- Missed critical issues if miscategorized
- External service reliability impact

## Implementation Notes

1. **Configuration Management**
   - Store API keys in secrets management
   - Version control alert rules
   - Document threshold adjustments

2. **Monitoring**
   - Track alert response times
   - Monitor external service health
   - Review alert patterns weekly

3. **Documentation**
   - Maintain runbooks
   - Update response procedures
   - Track resolution patterns

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
