# Configuration Validation Dashboard

This Grafana dashboard provides comprehensive monitoring for the IOTA configuration validation system. It visualizes key metrics collected by the validation process and provides alerting capabilities for critical issues.

## Features

### 1. Error Monitoring
- Real-time tracking of configuration validation errors
- Alert threshold: > 10 errors in 5 minutes
- Shows current count and maximum values
- Trend visualization over time

### 2. Warning Tracking
- Monitors configuration validation warnings
- Alert threshold: > 20 warnings in 5 minutes
- Tracks warning trends and patterns
- Helps identify potential configuration issues early

### 3. Security Issue Detection
- Zero-tolerance monitoring of security-related issues
- Immediate alerting on any security concern
- Critical priority visualization
- Historical security issue tracking

### 4. Performance Metrics
- Validation duration tracking
- Statistical analysis (avg, min, max)
- Performance trend visualization
- Helps identify performance degradation

### 5. Validation Freshness
- Last validation timestamp monitoring
- Visual indicators for stale validations
- Helps ensure regular validation execution
- Configurable staleness thresholds

## Setup Instructions

1. **Prerequisites**
   - Grafana v7.0 or later
   - Prometheus data source configured
   - IOTA metrics exporter running

2. **Dashboard Import**
   ```bash
   # From the Grafana UI:
   1. Click '+ Import' in the dashboard section
   2. Upload 'validation_dashboard.json'
   3. Select your Prometheus data source
   ```

3. **Configure Data Source**
   - Ensure Prometheus is scraping metrics from:
     ```yaml
     - job_name: 'iota_validation'
       static_configs:
         - targets: ['localhost:9090']
       scrape_interval: 10s
     ```

4. **Alert Configuration**
   - Configure notification channels in Grafana
   - Update alert thresholds if needed:
     - Errors: Currently set to 10/5min
     - Warnings: Currently set to 20/5min
     - Security: Any non-zero value
     - Validation staleness: > 15min

## Metrics

| Metric Name | Type | Description |
|------------|------|-------------|
| config_validation_errors | Counter | Total number of validation errors |
| config_validation_warnings | Counter | Total number of validation warnings |
| config_validation_security_issues | Counter | Number of security-related issues |
| config_validation_duration_seconds | Gauge | Time taken for validation execution |
| config_validation_last_timestamp | Gauge | Unix timestamp of last validation |

## Dashboard Panels

1. **Configuration Validation Errors**
   - Graph showing error count over time
   - Alert threshold line at 10 errors
   - Current and max values displayed

2. **Configuration Validation Warnings**
   - Warning count visualization
   - Trend analysis
   - Alert threshold at 20 warnings

3. **Security Issues**
   - Critical security issue monitoring
   - Immediate alerting on any issues
   - Historical tracking

4. **Validation Duration**
   - Performance tracking
   - Statistical analysis
   - Trend visualization

5. **Last Validation Time**
   - Timestamp of most recent validation
   - Visual staleness indicator
   - Quick status overview

## Customization

### Alert Thresholds
Modify alert thresholds in each panel's Alert tab:
```yaml
# Example: Modify error threshold
- alert: High Error Rate
  expr: config_validation_errors > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    description: "High number of validation errors detected"
```

### Time Ranges
- Default range: Last 1 hour
- Refresh rate: 10 seconds
- Configurable time picker available

### Visual Adjustments
- Dark theme by default
- Configurable colors and thresholds
- Adjustable graph styles

## Troubleshooting

1. **No Data**
   - Verify metrics exporter is running
   - Check Prometheus scrape configuration
   - Validate metric names match exporter

2. **Stale Metrics**
   - Check validation service status
   - Verify scrape interval configuration
   - Check for network connectivity issues

3. **Alert Issues**
   - Verify notification channel setup
   - Check alert rule configuration
   - Validate threshold values

## Maintenance

- Regularly review alert thresholds
- Monitor dashboard performance
- Update visualization as new metrics are added
- Backup dashboard configuration

## Support

For issues or questions:
- Check the IOTA documentation
- Review Grafana's documentation
- Contact the development team

## Version History

- v1.0.0 - Initial release
  - Basic metric visualization
  - Standard alert thresholds
  - Performance monitoring
