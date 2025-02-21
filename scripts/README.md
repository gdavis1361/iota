# Configuration Error Logging Script

## Overview
The `check_config_errors.sh` script is a robust tool for parsing and analyzing configuration error logs. It supports filtering by date, error type, and custom patterns while handling various timestamp formats and timezone configurations.

## Features
- Flexible argument parsing (`--option=value` or `--option value` formats)
- Date-based filtering with timezone support
- Error type filtering (validation/init)
- Custom error pattern matching
- Colorized output (optional)
- Warning message display (optional)
- Summary mode for aggregated results

## Usage
```bash
./check_config_errors.sh [options] <log_file> [<log_file>...]

Options:
  -h, --help           Display this help message
  -t, --type TYPE      Filter by error type (validation|init)
  -p, --pattern PAT    Filter by custom error pattern
  --days N             Show only errors from last N days
  --color             Enable colored output
  --no-color          Disable colored output
  --show-warnings     Include warning messages
  --summary           Show only error count summary
```

## Environment Variables
- `CURRENT_TIME`: Override the current time for testing (ISO 8601 format)
  Example: `CURRENT_TIME="2025-02-21T09:28:02-05:00"`

## Examples
1. Show errors from last 7 days:
   ```bash
   ./check_config_errors.sh --days=7 app.log
   ```

2. Filter validation errors with color:
   ```bash
   ./check_config_errors.sh --type validation --color app.log
   ```

3. Show summary of multiple log files:
   ```bash
   ./check_config_errors.sh --summary app.log backup.log
   ```

## Date Handling
- Supports ISO 8601 timestamps (e.g., "2025-02-21T09:28:02-05:00")
- Handles UTC and local timezone offsets
- Uses system time if `CURRENT_TIME` is not set

## Error Types
1. **Validation Errors**: Configuration validation failures
2. **Init Errors**: Initialization and startup errors

## Exit Codes
- 0: Success (errors may still be found)
- 1: Script usage error or missing files

## Dependencies
- bash 4.0+
- date command with GNU coreutils
- grep, sed, awk

## Testing
Run the test suite:
```bash
cd tests/scripts && bats test_check_config_errors.sh
```

## Development Notes

### Key Functions
- `parse_arguments`: Handles command-line argument parsing
- `process_log_entry`: Processes individual log entries
- `should_process_entry`: Validates entry against filters
- `print_summary`: Generates error summary report

### Error Message Format
Messages are formatted consistently:
```
[ERROR] <timestamp>: <message>
```

### Performance Considerations
- Processes logs in a single pass
- Minimizes subshell usage
- Direct output instead of buffering

### Known Edge Cases
1. Logs with mixed timestamp formats
2. Files with very long lines
3. Timezone conversion edge cases

## Contributing
1. Ensure all tests pass
2. Add tests for new features
3. Follow existing code style
4. Update documentation
