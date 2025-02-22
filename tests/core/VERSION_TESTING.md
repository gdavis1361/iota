# Configuration Version Testing Guide

## Overview

This guide covers testing strategies for configuration version management, ensuring that version validation, migration paths, and monitoring work as expected.

## Test Categories

### 1. Version Validation Tests

```python
def test_config_monitor_version_mismatch():
    """Test version mismatch detection."""
    monitor = ConfigurationMonitor.get_instance()

    # Test with old version
    settings = Settings(
        SECRET_KEY="x" * 32,
        ENVIRONMENT="test",
        version=ConfigVersion.V1_0.value
    )

    # Verify mismatch detection
    metrics = monitor.get_metrics()
    assert metrics["config_version"] != metrics["schema_version"]
    assert metrics["total_warnings"] > 0
```

### 2. Migration Path Testing

Test configuration migration from V1.0 to V2.0:

```bash
# Test environment setup
export VERSION="1.0"
export SECRET_KEY="test-key-32-chars-long-example-key"
export ENVIRONMENT="test"

# Run migration validation
python -m pytest tests/core/test_config_migration.py -v
```

### 3. Monitoring Tests

Verify metrics collection and warning generation:

```python
def test_version_monitoring():
    """Test version monitoring metrics."""
    monitor = ConfigurationMonitor.get_instance()

    # Check metrics
    metrics = monitor.get_metrics()
    assert "config_version" in metrics
    assert "schema_version" in metrics
    assert isinstance(metrics["total_warnings"], int)
```

## Test Scenarios

### Version Validation

1. **Valid Current Version**
   - Use V2.0 configuration
   - Expect no warnings
   - Verify metrics

2. **Legacy Version**
   - Use V1.0 configuration
   - Expect version mismatch warning
   - Check warning counter

3. **Invalid Version**
   - Use non-existent version
   - Expect validation error
   - Verify error handling

### Migration Testing

1. **V1.0 to V2.0 Migration**
   - Start with V1.0 config
   - Apply migration steps
   - Verify V2.0 compatibility

2. **Configuration Updates**
   - Check required field additions
   - Verify deprecated field handling
   - Test validation rules

### Monitoring Verification

1. **Metrics Collection**
   - Check version tracking
   - Verify warning counts
   - Test performance metrics

2. **Health Checks**
   - Verify status reporting
   - Check version status
   - Test alert conditions

## Test Environment Setup

```bash
# Set up test environment
cp tests/.env.test.example tests/.env.test

# Required environment variables
export VERSION="2.0"
export SECRET_KEY="test-key-32-chars-long-example-key"
export ENVIRONMENT="test"
```

## Running Tests

```bash
# Run all version-related tests
python -m pytest tests/core/test_config_monitoring.py -v

# Run specific test categories
python -m pytest tests/core/test_config_monitoring.py::test_config_monitor_version_mismatch -v
```

## Test Coverage

Ensure tests cover:
- Version validation
- Migration paths
- Monitoring metrics
- Error handling
- Security validation

## Common Issues

1. **Version Mismatch Detection**
   - Symptom: Warnings not generated
   - Check: Monitor initialization
   - Solution: Reset monitor state

2. **Migration Failures**
   - Symptom: Validation errors
   - Check: Required fields
   - Solution: Update config

3. **Metric Collection Issues**
   - Symptom: Missing metrics
   - Check: Monitor singleton
   - Solution: Verify instance

## Best Practices

1. **Test Isolation**
   ```python
@pytest.fixture(autouse=True)
def reset_monitor():
    ConfigurationMonitor._instance = None
    yield
```

2. **Environment Control**
   ```python
def test_version_validation():
    config = {
        "version": "1.0.0",
        "settings": {
            "timeout": 30,
            "retries": 3
        }
    }
    assert validate_config_version(config)
```

3. **Comprehensive Validation**
   ```python
def test_full_validation():
    """Test complete configuration validation."""
    settings = Settings(
        SECRET_KEY="x" * 32,
        ENVIRONMENT="test",
        version=ConfigVersion.V2_0.value
    )
    monitor = ConfigurationMonitor.get_instance()
    metrics = monitor.get_metrics()

    assert metrics["total_validations"] > 0
    assert metrics["total_errors"] == 0
    assert metrics["config_version"] == ConfigVersion.V2_0.value
```

## Security Testing

1. **Version Validation Security**
   - Test invalid version formats
   - Verify environment restrictions
   - Check secret validation

2. **Migration Security**
   - Validate sensitive fields
   - Test environment controls
   - Verify access restrictions

## CI/CD Integration

```yaml
version_tests:
  script:
    - python -m pytest tests/core/test_config_monitoring.py -v
    - python -m pytest tests/core/test_config_migration.py -v
  artifacts:
    reports:
      coverage: coverage.xml
```

## Future Considerations

1. **Version 3.0 Testing**
   - Plan migration tests
   - Update validation rules
   - Add new metrics

2. **Automated Testing**
   - Consider property-based testing
   - Add performance benchmarks
   - Implement security scans
