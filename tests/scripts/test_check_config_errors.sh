#!/bin/bash

# Test suite for check_config_errors.sh
# Uses BATS (Bash Automated Testing System)

setup() {
    # Create temporary directory for test logs
    export TEST_DIR="$(mktemp -d)"
    export CURRENT_TIME="2025-02-21T09:28:02-05:00"
    
    # Create sample log files with various timestamps
    cat > "$TEST_DIR/config1.log" << EOF
{"timestamp": "2025-02-21T09:14:45-05:00", "level": "ERROR", "message": "Configuration validation error", "category": "CONFIG_VALIDATION", "extra": {"field": "SENTRY_DSN", "error": "Invalid format"}}
{"timestamp": "2025-02-21T09:15:30-05:00", "level": "CRITICAL", "message": "Failed to initialize", "category": "CONFIG_INIT", "extra": {"error": "Missing fields"}}
{"timestamp": "2025-02-20T09:15:30-05:00", "level": "ERROR", "message": "Old validation error", "category": "CONFIG_VALIDATION", "extra": {"field": "OLD_FIELD", "error": "Old error"}}
EOF
    
    cat > "$TEST_DIR/config2.log" << EOF
{"timestamp": "2025-02-21T09:17:45-05:00", "level": "ERROR", "message": "Configuration validation error", "category": "CONFIG_VALIDATION", "extra": {"field": "API_KEY", "error": "Required"}}
{"timestamp": "2025-02-21T09:18:00-05:00", "level": "WARNING", "message": "Config warning", "category": "CONFIG_WARNING", "extra": {"detail": "Non-critical issue"}}
EOF

    # Create a log with invalid JSON
    cat > "$TEST_DIR/invalid.log" << EOF
{"timestamp": "2025-02-21T09:20:00-05:00", "level": "ERROR"
{"timestamp": "2025-02-21T09:21:00-05:00", "level": "ERROR", "message": "Valid error", "category": "CONFIG_VALIDATION"}
EOF

    # Create a log with different timezone
    cat > "$TEST_DIR/timezone.log" << EOF
{"timestamp": "2025-02-21T14:28:00Z", "level": "ERROR", "message": "UTC error", "category": "CONFIG_VALIDATION"}
EOF
}

teardown() {
    # Clean up temporary directory
    rm -rf "$TEST_DIR"
}

@test "Script shows help message with -h" {
    run ./scripts/check_config_errors.sh -h
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Usage:" ]]
}

@test "Script requires log file argument" {
    run ./scripts/check_config_errors.sh
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Error: No log files specified" ]]
}

@test "Script handles non-existent files" {
    run ./scripts/check_config_errors.sh nonexistent.log
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Error: File not found" ]]
}

@test "Script processes single log file" {
    run ./scripts/check_config_errors.sh "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors:" ]]
    [[ "${output}" =~ "SENTRY_DSN" ]]
}

@test "Script processes multiple log files" {
    run ./scripts/check_config_errors.sh "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "SENTRY_DSN" ]]
    [[ "${output}" =~ "API_KEY" ]]
}

@test "Script filters by error type" {
    run ./scripts/check_config_errors.sh -t validation "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors:" ]]
    [[ ! "${output}" =~ "Configuration Initialization Errors:" ]]
}

@test "Script counts errors correctly" {
    run ./scripts/check_config_errors.sh "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Validation Errors: 2" ]]
    [[ "${output}" =~ "Critical Errors: 1" ]]
}

@test "Script handles empty log files" {
    touch "$TEST_DIR/empty.log"
    run ./scripts/check_config_errors.sh "$TEST_DIR/empty.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Validation Errors: 0" ]]
    [[ "${output}" =~ "Critical Errors: 0" ]]
}

@test "Script filters by date correctly" {
    run ./scripts/check_config_errors.sh --days=1 "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "SENTRY_DSN" ]]
    [[ ! "${output}" =~ "OLD_FIELD" ]]
}

@test "Script handles different timezones" {
    run ./scripts/check_config_errors.sh "$TEST_DIR/timezone.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "UTC error" ]]
}

@test "Script handles invalid JSON gracefully" {
    run ./scripts/check_config_errors.sh "$TEST_DIR/invalid.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Warning: Invalid JSON entry found" ]]
    [[ "${output}" =~ "Valid error" ]]
}

@test "Script supports pattern matching" {
    run ./scripts/check_config_errors.sh -p "API_KEY|SENTRY" "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "SENTRY_DSN" ]]
    [[ "${output}" =~ "API_KEY" ]]
    [[ ! "${output}" =~ "OLD_FIELD" ]]
}

@test "Script colorizes output correctly" {
    run ./scripts/check_config_errors.sh --color "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ $'\033[' ]]  # ANSI escape sequence
}

@test "Script disables color when requested" {
    run ./scripts/check_config_errors.sh --no-color "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ ! "${output}" =~ $'\033[' ]]  # No ANSI escape sequence
}

@test "Script handles warning level messages" {
    run ./scripts/check_config_errors.sh --show-warnings "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Config warning" ]]
    [[ "${output}" =~ "Non-critical issue" ]]
}

@test "Script summarizes errors by category" {
    run ./scripts/check_config_errors.sh --summary "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Error Summary by Category:" ]]
    [[ "${output}" =~ "CONFIG_VALIDATION:" ]]
    [[ "${output}" =~ "CONFIG_INIT:" ]]
}
