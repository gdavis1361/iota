# IOTA Testing Documentation

## Overview
This document describes the testing procedures for the IOTA configuration error logging system, including performance testing and validation procedures.

## Quick Start

### Validation Testing
To run a quick validation test:
```bash
cd tests/scripts
./performance_test.sh --validate
```
This will:
- Run a single test pass with a small dataset (10 entries)
- Display system information and test progress
- Complete within seconds
- Exit automatically after completion

### Full Performance Testing
For comprehensive performance testing:
```bash
cd tests/scripts
./performance_test.sh
```
This will run tests with:
- Small dataset (10 entries)
- Medium dataset (100 entries)
- Large dataset (1000 entries)

## Test Modes

### Validation Mode
- Purpose: Quick verification of basic functionality
- Dataset: 10 test entries
- Duration: < 1 second
- Command: `--validate` flag
- Output: Includes script startup info, system details, and test completion markers

### Full Test Mode
- Purpose: Comprehensive performance assessment
- Datasets: Multiple sizes (10, 100, 1000 entries)
- Duration: Varies based on system
- Command: Run without flags
- Output: Detailed test results for each dataset size

## Output Format

### Validation Test Output
```
=== Performance Test Script Starting ===
Command line arguments: --validate
Current directory: /path/to/scripts
Script location: ./performance_test.sh

Validation mode activated
Will run single test with 10 entries

=== System Information ===
OS: <system>
Kernel: <version>
Shell: <shell>
Bash Version: <version>

=== Test Results ===
Dataset size: 10 entries
Start time: <timestamp>
...
Test complete: <timestamp>
```

### Test Data
- Format: One entry per line
- Location: Temporary files (automatically cleaned up)
- Content: Test entries with incrementing counters

## Best Practices

1. **Regular Validation**
   - Run validation tests before and after changes
   - Use `--validate` flag for quick checks
   - Verify test completion messages

2. **Performance Testing**
   - Run full suite for performance changes
   - Monitor system resource usage
   - Compare results across test runs

3. **Troubleshooting**
   - Check script permissions (`chmod +x`)
   - Verify correct working directory
   - Monitor system resources during tests

## Integration Testing

### Overview
Integration tests verify the interaction between components of the IOTA configuration system, including:
- Config file processing
- Error logging
- Performance monitoring
- System resource management

### Setup
```bash
# Set up test environment
cd tests/scripts
chmod +x setup_integration_tests.sh
./setup_integration_tests.sh
```

### Running Integration Tests

1. **Basic Integration Test**
```bash
./run_integration_tests.sh --basic
```
Verifies:
- Config file parsing
- Error logging format
- Basic performance metrics

2. **Full Integration Suite**
```bash
./run_integration_tests.sh --full
```
Tests:
- Cross-component communication
- Resource management
- Error handling chains
- Performance monitoring

3. **Component-Specific Tests**
```bash
./run_integration_tests.sh --component=config_parser
./run_integration_tests.sh --component=error_logger
./run_integration_tests.sh --component=perf_monitor
```

### Expected Output
```
=== Integration Test Suite ===
Component: config_parser
✓ Config file validation
✓ JSON schema verification
✓ Error format checking
✓ Performance metric collection

Component: error_logger
✓ Log file creation
✓ Error classification
✓ Timestamp verification
✓ Format compliance

Component: perf_monitor
✓ Resource tracking
✓ Metric collection
✓ Data aggregation
✓ Report generation

All integration tests passed!
```

### Common Integration Issues

1. **Component Communication Failure**
   ```
   ERROR: Failed to pass config data to error_logger
   ```
   Resolution:
   - Check component permissions
   - Verify IPC mechanisms
   - Ensure correct file paths

2. **Resource Lock Conflicts**
   ```
   ERROR: Cannot acquire lock on log file
   ```
   Resolution:
   - Clear stale locks: `./clear_locks.sh`
   - Check running processes
   - Verify file permissions

3. **Performance Metric Collection Failure**
   ```
   ERROR: Cannot collect system metrics
   ```
   Resolution:
   - Check system utilities
   - Verify monitoring permissions
   - Update system packages

## Enhanced Troubleshooting Guide

### Common Issues and Solutions

1. **Script Execution Failures**

   a. Permission Denied
   ```bash
   -bash: ./performance_test.sh: Permission denied
   ```
   Resolution:
   ```bash
   chmod +x performance_test.sh
   chmod +x check_config_errors.sh
   ```

   b. Missing Dependencies
   ```bash
   Error: jq command not found
   ```
   Resolution:
   ```bash
   # macOS
   brew install jq bc

   # Linux
   sudo apt-get install jq bc
   ```

2. **Data Processing Issues**

   a. Invalid JSON Format
   ```
   Error: parse error: Invalid JSON format
   ```
   Resolution:
   - Validate JSON: `jq '.' config.json`
   - Check file encoding: `file -I config.json`
   - Remove BOM: `sed '1s/^\xEF\xBB\xBF//' config.json`

   b. Timestamp Parse Errors
   ```
   Error: Invalid timestamp format
   ```
   Resolution:
   - Check timezone settings
   - Verify date format
   - Update system time

3. **Resource Usage Problems**

   a. High Memory Usage
   ```
   Error: Cannot allocate memory
   ```
   Resolution:
   - Reduce dataset size
   - Clear system cache
   - Check available memory

   b. Disk Space Issues
   ```
   Error: No space left on device
   ```
   Resolution:
   - Clean test results: `./cleanup_tests.sh`
   - Remove old logs
   - Check disk usage

4. **Performance Test Failures**

   a. Timeout Issues
   ```
   Error: Test exceeded timeout limit
   ```
   Resolution:
   - Adjust timeout: `--timeout 300`
   - Reduce dataset size
   - Check system load

   b. Resource Monitoring Failures
   ```
   Error: Cannot monitor system resources
   ```
   Resolution:
   - Check monitoring tools
   - Verify permissions
   - Update system utilities

### Diagnostic Commands

1. **System Status**
```bash
# Check system resources
./check_system.sh

# Verify dependencies
./verify_deps.sh

# Test file permissions
./check_permissions.sh
```

2. **Log Analysis**
```bash
# Analyze test logs
./analyze_logs.sh

# Check error patterns
./check_errors.sh

# Verify test results
./verify_results.sh
```

3. **Performance Diagnostics**
```bash
# Monitor resource usage
./monitor_resources.sh

# Check test execution times
./check_performance.sh

# Analyze bottlenecks
./analyze_bottlenecks.sh
```

### Recovery Procedures

1. **Test Environment Reset**
```bash
# Full reset
./reset_environment.sh

# Clean test data
./clean_test_data.sh

# Reset permissions
./reset_permissions.sh
```

2. **Emergency Cleanup**
```bash
# Stop all tests
./stop_all_tests.sh

# Remove locks
./clear_locks.sh

# Clean temporary files
./cleanup_temp.sh
```

## Monitoring and Metrics

### Resource Usage Tracking
- CPU utilization
- Memory consumption
- Disk I/O
- Network activity

### Performance Metrics
- Execution time
- Processing rate
- Response latency
- Resource efficiency

### System Limits
- Maximum file size
- Process count
- Open file handles
- Memory allocation

For more detailed information on specific components, refer to their respective documentation:
- [Config Parser Guide](../docs/config_parser.md)
- [Error Logger Guide](../docs/error_logger.md)
- [Performance Monitor Guide](../docs/perf_monitor.md)

## Future Enhancements

Planned improvements include:
- Enhanced performance metrics
- Extended cross-platform support
- Additional test datasets
- Improved resource monitoring

## Dependencies

Required:
- Bash shell
- Standard Unix utilities

Optional:
- Additional performance monitoring tools
- System resource monitoring utilities

## Notes

- All temporary files are automatically cleaned up
- Tests are designed to be non-destructive
- System resource impact is minimal
- Cross-platform compatibility is maintained
