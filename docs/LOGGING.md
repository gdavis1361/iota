# IOTA Configuration Logging System

## Overview

The IOTA configuration system implements comprehensive structured logging to help diagnose configuration issues and track system state. This document describes the logging system, its categories, and how to interpret log messages.

## Log Categories

### 1. Configuration Validation
Logs generated during configuration value validation.

#### Environment Validation
```json
{
    "level": "INFO",
    "message": "Environment validated",
    "extra": {
        "environment": "production"
    }
}
```

Error example:
```json
{
    "level": "ERROR",
    "message": "Configuration validation error",
    "extra": {
        "field": "ENVIRONMENT",
        "value": "invalid_env",
        "error": "Invalid environment 'invalid_env'. Must be one of: development, staging, production, test",
        "valid_options": ["development", "staging", "production", "test"]
    }
}
```

#### Sentry Configuration
```json
{
    "level": "INFO",
    "message": "Sentry DSN validated",
    "extra": {
        "field": "SENTRY_DSN"
    }
}
```

Error example:
```json
{
    "level": "ERROR",
    "message": "Configuration validation error",
    "extra": {
        "field": "SENTRY_DSN",
        "error": "Invalid Sentry DSN format",
        "pattern": "^https://[^:]+@[^/]+/\\d+$"
    }
}
```

#### Numeric Value Validation
```json
{
    "level": "INFO",
    "message": "Rate value validated",
    "extra": {
        "field": "SENTRY_TRACES_SAMPLE_RATE",
        "value": 0.1
    }
}
```

Error example:
```json
{
    "level": "ERROR",
    "message": "Configuration validation error",
    "extra": {
        "field": "ERROR_RATE_THRESHOLD",
        "value": 1.5,
        "error": "Rate value must be between 0 and 1"
    }
}
```

### 2. Configuration Initialization
Logs generated during configuration system initialization.

#### Successful Initialization
```json
{
    "level": "INFO",
    "message": "Settings initialized successfully",
    "extra": {
        "app_name": "iota",
        "environment": "production",
        "debug_mode": false,
        "log_level": "INFO",
        "sentry_enabled": true,
        "allowed_hosts": ["api.iota.com"]
    }
}
```

#### Initialization Failure
```json
{
    "level": "CRITICAL",
    "message": "Failed to initialize settings",
    "extra": {
        "error": "SECRET_KEY environment variable not set",
        "error_type": "ValidationError"
    }
}
```

## Log Levels

- **INFO**: Normal operational messages, successful validations
- **ERROR**: Configuration validation failures, missing required values
- **CRITICAL**: System-level failures that prevent initialization

## Sensitive Data Handling

The following fields are never logged:
- `SECRET_KEY`
- `SENTRY_DSN` (only validation status is logged)
- Database credentials
- API keys

## Troubleshooting Guide

### Common Issues and Their Log Patterns

1. **Missing Required Environment Variables**
   ```json
   {
       "level": "ERROR",
       "message": "Configuration validation error",
       "extra": {
           "field": "SECRET_KEY",
           "error": "Field required"
       }
   }
   ```
   Solution: Set the required environment variable in your .env file or deployment configuration.

2. **Invalid Environment Value**
   ```json
   {
       "level": "ERROR",
       "message": "Configuration validation error",
       "extra": {
           "field": "ENVIRONMENT",
           "value": "dev",
           "error": "Invalid environment 'dev'"
       }
   }
   ```
   Solution: Use one of the valid environment values: development, staging, production, or test.

3. **Invalid Numeric Values**
   ```json
   {
       "level": "ERROR",
       "message": "Configuration validation error",
       "extra": {
           "field": "SENTRY_TRACES_SAMPLE_RATE",
           "value": -0.1,
           "error": "Rate value must be between 0 and 1"
       }
   }
   ```
   Solution: Ensure all rate values are between 0 and 1, and threshold values are positive.

## Best Practices

1. **Log Monitoring**
   - Monitor ERROR and CRITICAL level logs for configuration issues
   - Set up alerts for repeated configuration validation failures
   - Track initialization failures as they indicate system-level issues

2. **Development**
   - Always check logs after configuration changes
   - Use the structured log data for automated testing
   - Keep sensitive information out of log messages

3. **Production**
   - Set appropriate log levels (INFO or higher recommended)
   - Monitor initialization logs during deployments
   - Set up log aggregation to track configuration issues across instances

## Integration with Log Aggregation

The structured logging format is designed to work with common log aggregation tools:

- **Elasticsearch**: JSON format enables direct indexing
- **CloudWatch**: Use JSON fields for metric filters
- **Splunk**: Use field names for search queries

Example Elasticsearch query to find all configuration validation errors:
```json
{
    "query": {
        "bool": {
            "must": [
                { "match": { "level": "ERROR" } },
                { "match": { "message": "Configuration validation error" } }
            ]
        }
    }
}
```

## Common Configuration Scenarios

### 1. Application Startup

During application startup, you'll see a sequence of validation and initialization logs:

```json
// Environment validation
{
    "timestamp": "2025-02-21T09:14:45-05:00",
    "level": "INFO",
    "message": "Environment validated",
    "category": "CONFIG_VALIDATION",
    "extra": {
        "environment": "production",
        "source": "environment_validator"
    }
}

// Sentry configuration
{
    "timestamp": "2025-02-21T09:14:45-05:00",
    "level": "INFO",
    "message": "Sentry configuration validated",
    "category": "CONFIG_VALIDATION",
    "extra": {
        "sentry_enabled": true,
        "environment": "production",
        "source": "sentry_validator"
    }
}

// Final initialization
{
    "timestamp": "2025-02-21T09:14:45-05:00",
    "level": "INFO",
    "message": "Settings initialized successfully",
    "category": "CONFIG_INIT",
    "extra": {
        "app_name": "iota",
        "environment": "production",
        "debug_mode": false,
        "log_level": "INFO"
    }
}
```

### 2. Configuration Validation Failures

Here are common validation failures and their log patterns:

#### Missing Required Environment Variables
```json
{
    "timestamp": "2025-02-21T09:14:45-05:00",
    "level": "ERROR",
    "message": "Configuration validation error",
    "category": "CONFIG_VALIDATION",
    "extra": {
        "field": "SECRET_KEY",
        "error": "Field required",
        "source": "settings_validator",
        "resolution": "Set SECRET_KEY in environment or .env file"
    }
}
```

#### Invalid Sentry Configuration
```json
{
    "timestamp": "2025-02-21T09:14:45-05:00",
    "level": "ERROR",
    "message": "Configuration validation error",
    "category": "CONFIG_VALIDATION",
    "extra": {
        "field": "SENTRY_DSN",
        "error": "Invalid Sentry DSN format",
        "source": "sentry_validator",
        "sentry_enabled": true,
        "resolution": "Check Sentry DSN format in project settings"
    }
}
```

#### Performance Monitoring Thresholds
```json
{
    "timestamp": "2025-02-21T09:14:45-05:00",
    "level": "ERROR",
    "message": "Configuration validation error",
    "category": "CONFIG_VALIDATION",
    "extra": {
        "field": "SLOW_REQUEST_THRESHOLD_MS",
        "value": "-100",
        "error": "Value must be positive",
        "source": "performance_validator",
        "resolution": "Set positive value for SLOW_REQUEST_THRESHOLD_MS"
    }
}
```

## Log Rotation Configuration

### Using logrotate (Linux/Unix)

Create a configuration file `/etc/logrotate.d/iota`:

```conf
/var/log/iota/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 iota iota
    sharedscripts
    postrotate
        systemctl reload iota >/dev/null 2>&1 || true
    endscript
}
```

### Python Logging Configuration

Configure rotating file handler in your logging setup:

```python
import logging
from logging.handlers import RotatingFileHandler
import json

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        return json.dumps(log_data)

def setup_logging(log_path: str):
    """Configure application logging with rotation."""
    handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=10_000_000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

## Log Parsing Scripts

### 1. Configuration Error Analysis Script

Create a file `scripts/analyze_config_errors.py`:

```python
#!/usr/bin/env python3
"""Analyze configuration errors from log files."""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class ConfigLogAnalyzer:
    """Analyzer for configuration logs."""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.errors: List[Dict] = []
        self.error_counts = Counter()
        self.field_errors = Counter()
        
    def load_logs(self, days: Optional[int] = None) -> None:
        """Load and parse log entries."""
        cutoff = None
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            
        with open(self.log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("level") == "ERROR" and "CONFIG" in entry.get("category", ""):
                        if cutoff:
                            log_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                            if log_time < cutoff:
                                continue
                                
                        self.errors.append(entry)
                        self.error_counts[entry["message"]] += 1
                        if "field" in entry.get("extra", {}):
                            self.field_errors[entry["extra"]["field"]] += 1
                except (json.JSONDecodeError, KeyError):
                    continue
    
    def print_summary(self) -> None:
        """Print error analysis summary."""
        print("\n=== Configuration Error Analysis ===\n")
        
        print("Total Errors:", len(self.errors))
        
        print("\nTop Error Messages:")
        for msg, count in self.error_counts.most_common(5):
            print(f"  {count:3d}: {msg}")
            
        print("\nMost Problematic Fields:")
        for field, count in self.field_errors.most_common(5):
            print(f"  {count:3d}: {field}")
            
        print("\nRecent Error Examples:")
        for error in self.errors[-3:]:
            print(f"\n  Time: {error['timestamp']}")
            print(f"  Message: {error['message']}")
            print(f"  Details: {json.dumps(error.get('extra', {}), indent=2)}")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: analyze_config_errors.py <log_file> [days]")
        sys.exit(1)
        
    log_file = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    analyzer = ConfigLogAnalyzer(log_file)
    analyzer.load_logs(days)
    analyzer.print_summary()

if __name__ == "__main__":
    main()
```

### 2. Quick Error Check Script

Create a file `scripts/check_config_errors.sh`:

```bash
#!/bin/bash
# Quick check for configuration errors in recent logs

LOG_FILE="${1:-/var/log/iota/config.log}"
HOURS="${2:-24}"

echo "Checking configuration errors in the last $HOURS hours..."

# Find error patterns
echo -e "\nConfiguration Validation Errors:"
grep -i "CONFIG_VALIDATION.*ERROR" "$LOG_FILE" | tail -n 5

echo -e "\nConfiguration Initialization Errors:"
grep -i "CONFIG_INIT.*CRITICAL" "$LOG_FILE" | tail -n 5

# Count errors by type
echo -e "\nError Counts by Category:"
grep -i "ERROR" "$LOG_FILE" | grep -o '"category":"[^"]*"' | sort | uniq -c | sort -nr

# Check for specific critical issues
echo -e "\nMissing Required Fields:"
grep -i "Field required" "$LOG_FILE" | grep -o '"field":"[^"]*"' | sort | uniq -c | sort -nr
```

### Using the Scripts

1. Configuration Error Analysis:
```bash
# Analyze all configuration errors
python scripts/analyze_config_errors.py /var/log/iota/config.log

# Analyze errors from the last 7 days
python scripts/analyze_config_errors.py /var/log/iota/config.log 7
```

Example output:
```
=== Configuration Error Analysis ===

Total Errors: 15

Top Error Messages:
   5: Configuration validation error
   3: Missing required field
   2: Invalid value format

Most Problematic Fields:
   3: SECRET_KEY
   2: SENTRY_DSN
   2: ENVIRONMENT

Recent Error Examples:

  Time: 2025-02-21T09:16:04-05:00
  Message: Configuration validation error
  Details: {
    "field": "SECRET_KEY",
    "error": "Field required",
    "source": "settings_validator"
  }
```

2. Quick Error Check:
```bash
# Check errors in the last 24 hours
./scripts/check_config_errors.sh /var/log/iota/config.log

# Check errors in the last 48 hours
./scripts/check_config_errors.sh /var/log/iota/config.log 48
```

Example output:
```
Checking configuration errors in the last 24 hours...

Configuration Validation Errors:
2025-02-21 09:14:45 ERROR Configuration validation error: Invalid Sentry DSN format
2025-02-21 09:15:12 ERROR Configuration validation error: Field required SECRET_KEY

Configuration Initialization Errors:
2025-02-21 09:14:45 CRITICAL Failed to initialize settings: Missing required fields

Error Counts by Category:
     15 "category":"CONFIG_VALIDATION"
      3 "category":"CONFIG_INIT"

Missing Required Fields:
      3 "field":"SECRET_KEY"
      2 "field":"SENTRY_DSN"
```
