# Configuration Guide

## Overview

This document details the configuration system for the IOTA project, including validation rules, requirements, and troubleshooting guidance.

## Environment Variables

### Required Configuration

| Variable | Description | Required | Default | Validation Rules |
|----------|-------------|----------|---------|-----------------|
| `ENVIRONMENT` | Application environment | Yes | `development` | Must be one of: `development`, `testing`, `staging`, `production` |
| `SECRET_KEY` | Application secret key | Yes | None | Minimum 32 characters |
| `DEBUG` | Debug mode flag | No | `false` | Must be `false` in production |
| `ALLOWED_HOSTS` | Allowed host domains | Yes | `["localhost", "127.0.0.1"]` | JSON array format; No wildcards in production |
| `SENTRY_ENABLED` | Enable Sentry error tracking | No | `false` | Boolean value |
| `SENTRY_DSN` | Sentry service DSN | If Sentry enabled | None | Must be valid HTTP(S) URL |

## Validation Rules

### Environment Validation
- Valid environment values:
  - `development`: Local development environment
  - `testing`: Test environment
  - `staging`: Pre-production environment
  - `production`: Production environment
- Case-insensitive matching
- Error if invalid environment specified

### Security Settings
- `SECRET_KEY`:
  - Minimum length: 32 characters
  - Error Message: "SECRET_KEY is too short (minimum 32 characters)"
  - Used for cryptographic operations
  - Should be unique per environment
  - Never commit to version control

### Production Environment Rules
- `DEBUG` must be `false`
  - Error Message: "DEBUG should not be enabled in production"
  - Security Risk: Exposing debug information in production
- `ALLOWED_HOSTS` restrictions:
  - No wildcard (`*`) entries allowed
  - Must be explicit domain list
  - Error Message: "Wildcard ALLOWED_HOSTS should not be used in production"

### Sentry Configuration
- When `SENTRY_ENABLED` is `true`:
  - `SENTRY_DSN` is required
  - Must start with `http://` or `https://`
  - Error Messages:
    - "SENTRY_DSN is required when Sentry is enabled"
    - "SENTRY_DSN must start with http:// or https://"

## Configuration Examples

### Development Environment
```env
ENVIRONMENT=development
SECRET_KEY=your-secure-secret-key-minimum-32-chars
DEBUG=true
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
SENTRY_ENABLED=false
```

### Production Environment
```env
ENVIRONMENT=production
SECRET_KEY=your-production-secret-key-minimum-32-chars
DEBUG=false
ALLOWED_HOSTS=["api.example.com", "www.example.com"]
SENTRY_ENABLED=true
SENTRY_DSN=https://your-sentry-dsn.ingest.sentry.io/project-id
```

## Validation Process

The configuration validation system performs the following checks:

1. Environment validation
2. Security settings validation
3. Sentry configuration validation
4. Allowed hosts validation

Each validation step produces specific error messages in case of failures, categorized as:
- Errors: Critical issues that must be fixed
- Warnings: Potential issues to review
- Security Concerns: Security-related issues that need attention

## Metrics and Monitoring

### Validation Metrics

The configuration validation system now collects and outputs metrics to help monitor the health of your configuration. These metrics are stored in `validation_metrics.json`.

#### Metric Types

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `error_count` | Number of validation errors | 10 |
| `warning_count` | Number of validation warnings | 20 |
| `security_count` | Number of security issues | 0 |
| `validation_time_ms` | Time taken for validation | N/A |

#### Metrics JSON Structure

```json
{
  "error_count": 0,
  "warning_count": 0,
  "security_count": 0,
  "validation_time_ms": 123.45,
  "errors": [],
  "warnings": [],
  "security_concerns": [],
  "last_validation": "2025-02-21T22:04:50-05:00"
}
```

### Alert Configuration

The system supports multiple notification channels for configuration issues:

#### Slack Alerts
- Triggered for security concerns
- Includes validation metrics
- Real-time notifications

#### Email Alerts
- Triggered for validation errors
- Daily summary of warnings
- Includes troubleshooting tips

#### Alert Thresholds
- Error threshold: 10 errors
- Warning threshold: 20 warnings
- Security threshold: 0 issues
- Aggregation window: 5 minutes

### Monitoring Integration

The `metrics.json` output can be integrated with monitoring systems:

1. **Prometheus Integration**
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'config_validation'
       static_configs:
         - targets: ['localhost:9090']
       metrics_path: '/metrics'
   ```

2. **Grafana Dashboard**
   - Import the provided dashboard template
   - Configure data source
   - Set up alerts based on thresholds

### Performance Monitoring

Monitor validation performance metrics:
- Validation execution time
- Rule parsing overhead
- Memory usage patterns
- Cache hit rates

## Troubleshooting

### Common Issues

1. Invalid Environment
   - **Symptom**: "Invalid ENVIRONMENT value: {value}"
   - **Solution**: Set ENVIRONMENT to one of the allowed values

2. Short Secret Key
   - **Symptom**: "SECRET_KEY is too short (minimum 32 characters)"
   - **Solution**: Generate a new secret key with at least 32 characters

3. Production Debug Mode
   - **Symptom**: "DEBUG should not be enabled in production"
   - **Solution**: Set DEBUG=false in production environment

4. Invalid Allowed Hosts
   - **Symptom**: "ALLOWED_HOSTS must be a valid JSON array"
   - **Solution**: Ensure ALLOWED_HOSTS is a valid JSON array of strings

5. Sentry Configuration
   - **Symptom**: "SENTRY_DSN is required when Sentry is enabled"
   - **Solution**: Provide valid Sentry DSN or disable Sentry

## Best Practices

1. Environment Management
   - Use different configurations per environment
   - Store sensitive values in environment variables
   - Use `.env` files for local development only

2. Security
   - Generate strong secret keys
   - Restrict allowed hosts in production
   - Keep debug mode disabled in production
   - Regularly rotate sensitive credentials

3. Monitoring
   - Enable Sentry in production for error tracking
   - Monitor configuration validation metrics
   - Review security concerns regularly

## Configuration Updates

When updating configuration:
1. Run validation checks locally
2. Test in lower environments first
3. Document any new configuration requirements
4. Update CI/CD pipeline configuration
5. Create backup of existing configuration

## Future Considerations

- Dynamic validation rules via configuration file
- Additional security validations
- Custom environment-specific rules
- Integration with secrets management
- Automated configuration testing
