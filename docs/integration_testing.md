# Integration Testing Guide

## Metrics and Monitoring Integration Tests

This guide covers the integration testing infrastructure for IOTA's metrics collection and monitoring system.

### Test Environment Setup

#### Prerequisites
- Python 3.9+ with `pip`
- Docker (for Prometheus container)
- Required Python packages:
  ```
  requests
  prometheus_client
  pytest-timeout
  ```

#### Environment Variables
```bash
ENVIRONMENT=test
METRICS_PORT=9090
SECRET_KEY=your_test_key
```

### Running Integration Tests

1. **Start Prometheus Container**
   ```bash
   docker run -d \
     --name prometheus-test \
     -p 9090:9090 \
     prom/prometheus:v2.45.0
   ```

2. **Start Metrics Exporter**
   ```bash
   python scripts/metrics_exporter.py &
   # Wait 5 seconds for startup
   sleep 5
   ```

3. **Run Tests**
   ```bash
   pytest tests/test_metrics_integration.py -v
   ```

### Test Cases Overview

#### 1. Endpoint Availability (`test_metrics_endpoint_availability`)
- **Purpose**: Verifies metrics endpoint is accessible
- **Checks**:
  - Endpoint returns 200 status
  - Content-Type is text/plain
- **Failure Scenarios**:
  - Endpoint not responding
  - Wrong content type

#### 2. Required Metrics (`test_required_metrics_present`)
- **Purpose**: Ensures all required metrics exist
- **Metrics Checked**:
  - `config_validation_errors`
  - `config_validation_warnings`
  - `config_validation_security_issues`
  - `config_validation_duration_seconds`
  - `config_validation_last_timestamp`
- **Failure Scenarios**:
  - Missing metrics
  - Incorrect metric names

#### 3. Metric Types (`test_metric_type_validation`)
- **Purpose**: Validates metric types
- **Type Mappings**:
  - Counters:
    - `config_validation_errors`
    - `config_validation_warnings`
    - `config_validation_security_issues`
  - Gauges:
    - `config_validation_duration_seconds`
    - `config_validation_last_timestamp`
- **Failure Scenarios**:
  - Wrong metric type
  - Type conversion errors

#### 4. Metric Updates (`test_metric_updates`)
- **Purpose**: Tests metric value updates
- **Checks**:
  - Counter increments
  - Value persistence
- **Failure Scenarios**:
  - Values not updating
  - Incorrect increment amounts

#### 5. Duration Tracking (`test_duration_tracking`)
- **Purpose**: Validates duration measurements
- **Checks**:
  - Timing accuracy
  - Value ranges
- **Failure Scenarios**:
  - Negative durations
  - Missing measurements

#### 6. Timestamp Updates (`test_timestamp_updates`)
- **Purpose**: Checks timestamp tracking
- **Checks**:
  - Timestamp freshness
  - Update frequency
- **Failure Scenarios**:
  - Stale timestamps
  - Future timestamps

#### 7. Metric Labels (`test_metric_labels`)
- **Purpose**: Verifies label presence
- **Required Labels**:
  - environment
  - version
- **Failure Scenarios**:
  - Missing labels
  - Invalid label values

#### 8. Help Text (`test_metric_help_text`)
- **Purpose**: Validates metric documentation
- **Checks**:
  - Help text presence
  - Content length
- **Failure Scenarios**:
  - Missing documentation
  - Insufficient descriptions

### Troubleshooting Guide

#### Common Issues

1. **Port Conflicts**
   - **Symptom**: Prometheus or exporter fails to start
   - **Solution**: Check port usage and kill conflicting processes
   ```bash
   lsof -i :9090
   kill -9 <PID>
   ```

2. **Timeout Issues**
   - **Symptom**: Tests fail with timeout errors
   - **Solution**: Increase startup delay or test timeout
   ```bash
   pytest tests/test_metrics_integration.py --timeout=60
   ```

3. **Metric Registration Errors**
   - **Symptom**: "Duplicate metrics" errors
   - **Solution**: Use custom registry per test
   ```python
   from prometheus_client import CollectorRegistry
   registry = CollectorRegistry()
   ```

4. **Container Issues**
   - **Symptom**: Prometheus container not starting
   - **Solution**: Check Docker logs and cleanup
   ```bash
   docker logs prometheus-test
   docker rm -f prometheus-test
   ```

### CI/CD Integration

The integration tests run in CI with:
- Separate job from unit tests
- Prometheus container service
- 30-second test timeout
- Automatic cleanup

Example CI configuration:
```yaml
integration-test:
  services:
    prometheus:
      image: prom/prometheus:v2.45.0
      ports:
        - 9090:9090
  steps:
    - name: Run integration tests
      run: |
        python scripts/metrics_exporter.py &
        sleep 5
        pytest tests/test_metrics_integration.py -v --timeout=30
```

### Best Practices

1. **Test Isolation**
   - Use custom registry per test
   - Clean up resources after tests
   - Avoid global state

2. **Resource Management**
   - Stop containers after testing
   - Clean up background processes
   - Monitor resource usage

3. **Error Handling**
   - Validate error messages
   - Check edge cases
   - Test failure scenarios

### Future Considerations

1. **Dashboard Testing**
   - Automated dashboard validation
   - Visual regression testing
   - Alert rule verification

2. **Persistence Testing**
   - Metric storage validation
   - Data retention testing
   - Backup verification

3. **Distributed Testing**
   - Multi-node setup
   - Network partition handling
   - Consistency verification
