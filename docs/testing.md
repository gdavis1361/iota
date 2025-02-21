# Testing Guide

## Overview

This guide covers the testing infrastructure for the IOTA project, including:
- Setting up your development environment
- Running tests locally
- Understanding test coverage
- Working with mocks and fixtures
- CI/CD integration

## Development Setup

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Configure pre-commit hooks:
```bash
pre-commit install
```

## Running Tests

### Local Test Execution

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=server --cov=scripts --cov-report=term-missing
```

Run specific test file:
```bash
pytest tests/monitoring/test_performance_report.py
```

### Test Coverage Requirements

We maintain a minimum of 80% test coverage. Current coverage areas:
- Performance report generation
- Dashboard export functionality
- Error handling scenarios
- Configuration validation
- Metric calculations

## Working with Mocks

### Prometheus Mocks

Example of mocking Prometheus responses:
```python
@pytest.fixture
def mock_prometheus_data():
    return [{
        "values": [
            [1614556800, "10.5"],
            [1614556860, "11.2"]
        ]
    }]

def test_metric_calculation(mock_prom):
    # Test implementation
```

### Grafana API Mocks

Example of mocking Grafana API:
```python
@pytest.fixture
def mock_dashboard_data():
    return {
        "dashboard": {
            "uid": "abc123",
            "title": "Test Dashboard"
        }
    }
```

## Error Handling Tests

Test various error scenarios:
- API timeouts
- Invalid responses
- Network errors
- Authentication failures

Example:
```python
@pytest.mark.parametrize("error_type", [
    ConnectionError,
    TimeoutError,
    Exception
])
def test_error_handling(mock_prom, error_type):
    # Test implementation
```

## CI/CD Integration

### GitHub Actions Workflow

Our CI pipeline runs on every push and pull request:
1. Code formatting (black, isort)
2. Linting (flake8)
3. Type checking (mypy)
4. Unit tests (pytest)
5. Coverage reporting

### Coverage Reports

Coverage reports are available:
- As CI artifacts (14-day retention)
- In pull request comments
- In the coverage.xml file

### Quality Checks

We enforce:
- 80% minimum test coverage
- Zero linting errors
- Type annotation compliance
- Consistent code formatting

## Best Practices

### Writing Tests

1. Use descriptive test names
2. One assertion per test
3. Proper setup and teardown
4. Clear error messages

### Mock Data

1. Use realistic test data
2. Avoid sensitive information
3. Document data structure
4. Version control mock files

### Error Testing

1. Test both success and failure
2. Verify error messages
3. Check error handling
4. Test edge cases

## Maintenance

### Regular Tasks

1. Update mock data
2. Review coverage reports
3. Update test dependencies
4. Clean up test artifacts

### Security Considerations

1. Never commit API keys
2. Use environment variables
3. Sanitize test data
4. Rotate test credentials

## Troubleshooting

### Common Issues

1. Redis connection errors:
   - Ensure Redis is running
   - Check port configuration

2. Prometheus query failures:
   - Verify mock data format
   - Check query syntax

3. Coverage drops:
   - Identify uncovered code
   - Add missing test cases

### Getting Help

1. Check CI logs
2. Review test output
3. Consult documentation
4. Ask team for help

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Mock Object Library](https://docs.python.org/3/library/unittest.mock.html)
