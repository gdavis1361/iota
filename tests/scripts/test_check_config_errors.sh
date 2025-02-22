#!/usr/bin/env bats

setup() {
    # Get the containing directory of this file
    TEST_DIR="$BATS_TEST_DIRNAME"
    SCRIPT_DIR="$TEST_DIR/../../scripts"

    # Create test log files
    cat > "$TEST_DIR/config1.log" << EOL
{"timestamp": "2025-02-21T09:28:02-05:00", "level": "ERROR", "message": "Configuration validation error", "category": "CONFIG_VALIDATION", "extra": {"field": "SENTRY_DSN", "error": "Invalid format"}}
{"timestamp": "2025-02-21T10:15:30-05:00", "level": "ERROR", "message": "Configuration validation error", "category": "CONFIG_VALIDATION", "extra": {"field": "API_KEY", "error": "Required"}}
{"timestamp": "2025-02-20T14:30:00-05:00", "level": "CRITICAL", "message": "Failed to initialize", "category": "CONFIG_INIT", "extra": {"error": "Missing fields"}}
EOL

    cat > "$TEST_DIR/config2.log" << EOL
{"timestamp": "2025-02-21T09:30:00-05:00", "level": "WARNING", "message": "Config warning", "category": "CONFIG_WARNING", "extra": {"detail": "Non-critical issue"}}
{"timestamp": "2025-02-21T09:35:00-05:00", "level": "WARNING", "message": "Config warning", "category": "CONFIG_WARNING", "extra": {"detail": "Another non-critical issue"}}
EOL

    cat > "$TEST_DIR/invalid.log" << EOL
{"timestamp": "2025-02-21T09:28:02-05:00", "level": "ERROR", "message": "Valid error", "category": "CONFIG_VALIDATION"}
Invalid JSON line
{"timestamp": "2025-02-21T09:29:02-05:00", "level": "ERROR", "message": "Another valid error", "category": "CONFIG_VALIDATION"}
EOL

    cat > "$TEST_DIR/timezone.log" << EOL
{"timestamp": "2025-02-21T14:28:02+00:00", "level": "ERROR", "message": "UTC error", "category": "CONFIG_VALIDATION"}
EOL

    # Set current time for tests
    export CURRENT_TIME="2025-02-21T09:28:02-05:00"

    # Ensure the script is executable
    chmod +x "$SCRIPT_DIR/check_config_errors.sh"
}

teardown() {
    # Clean up test files
    rm -f "$TEST_DIR"/*.log
    unset CURRENT_TIME
}

@test "Script shows help message with -h" {
    run "$SCRIPT_DIR/check_config_errors.sh" -h
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Usage:" ]]
}

@test "Script requires log file argument" {
    run "$SCRIPT_DIR/check_config_errors.sh"
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Error: No log files specified" ]]
}

@test "Script handles non-existent files" {
    run "$SCRIPT_DIR/check_config_errors.sh" nonexistent.log
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Error: File not found" ]]
}

@test "Script processes single log file" {
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors" ]]
    [[ "${output}" =~ "SENTRY_DSN" ]]
}

@test "Script processes multiple log files" {
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "SENTRY_DSN" ]]
    [[ "${output}" =~ "API_KEY" ]]
}

@test "Script filters by error type" {
    run "$SCRIPT_DIR/check_config_errors.sh" -t validation "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors" ]]
    [[ ! "${output}" =~ "Configuration Initialization Errors" ]]
}

@test "Script counts errors correctly" {
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Validation Errors: 2" ]]
    [[ "${output}" =~ "Critical Errors: 1" ]]
}

@test "Script handles empty log files" {
    touch "$TEST_DIR/empty.log"
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/empty.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Validation Errors: 0" ]]
    [[ "${output}" =~ "Critical Errors: 0" ]]
}

@test "Script filters by date correctly" {
    run "$SCRIPT_DIR/check_config_errors.sh" --days=1 "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "SENTRY_DSN" ]]
    [[ ! "${output}" =~ "OLD_FIELD" ]]
}

@test "Script handles different timezones" {
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/timezone.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "UTC error" ]]
}

@test "Script handles invalid JSON gracefully" {
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/invalid.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Warning: Invalid JSON entry found" ]]
    [[ "${output}" =~ "Valid error" ]]
}

@test "Script supports pattern matching" {
    run "$SCRIPT_DIR/check_config_errors.sh" -p "API_KEY|SENTRY" "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "SENTRY_DSN" ]]
    [[ "${output}" =~ "API_KEY" ]]
    [[ ! "${output}" =~ "OLD_FIELD" ]]
}

@test "Script colorizes output correctly" {
    run "$SCRIPT_DIR/check_config_errors.sh" --color "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ $'\033[' ]]  # ANSI escape sequence
}

@test "Script disables color when requested" {
    run "$SCRIPT_DIR/check_config_errors.sh" --no-color "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ ! "${output}" =~ $'\033[' ]]  # No ANSI escape sequence
}

@test "Script handles warning level messages" {
    run "$SCRIPT_DIR/check_config_errors.sh" --show-warnings "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Config warning" ]]
    [[ "${output}" =~ "Non-critical issue" ]]
}

@test "Script summarizes errors by category" {
    run "$SCRIPT_DIR/check_config_errors.sh" --summary "$TEST_DIR/config1.log" "$TEST_DIR/config2.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Error Summary by Category:" ]]
    [[ "${output}" =~ "CONFIG_VALIDATION:" ]]
    [[ "${output}" =~ "CONFIG_INIT:" ]]
}

# Test argument parsing with equals format
@test "argument parsing accepts --days=N format" {
    run "$SCRIPT_DIR/check_config_errors.sh" --days=2 "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors" ]]
}

# Test argument parsing with space format
@test "argument parsing accepts --days N format" {
    run "$SCRIPT_DIR/check_config_errors.sh" --days 2 "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors" ]]
}

# Test invalid days parameter
@test "argument parsing rejects invalid --days value" {
    run "$SCRIPT_DIR/check_config_errors.sh" --days=abc "$TEST_DIR/config1.log"
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" =~ "Error: --days requires a positive integer" ]]
}

# Test timezone handling with CURRENT_TIME
@test "handles different timezone offsets correctly" {
    export CURRENT_TIME="2025-02-21T15:00:00+00:00"  # UTC time
    run "$SCRIPT_DIR/check_config_errors.sh" --days=1 "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors" ]]
}

# Test multiple error types in single run
@test "processes multiple error types correctly" {
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Configuration Validation Errors" ]]
}

# Test summary mode with multiple files
@test "summary mode shows correct counts for multiple files" {
    run "$SCRIPT_DIR/check_config_errors.sh" --summary "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "Error Summary by Category:" ]]
}

# Test pattern matching with special characters
@test "pattern matching handles special characters" {
    run "$SCRIPT_DIR/check_config_errors.sh" -p "CONFIG_[A-Z]+" "$TEST_DIR/config1.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "CONFIG_" ]]
}

# Test empty file handling
@test "handles empty files gracefully" {
    echo -n > "$TEST_DIR/empty.log"
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/empty.log"
    [ "$status" -eq 0 ]
    [[ "${output}" =~ "No errors found" ]]
    rm -f "$TEST_DIR/empty.log"
}

# Test very long lines
@test "processes very long lines correctly" {
    long_line=$(printf 'E%.0s' {1..1000})  # Create a 1000-character line
    echo "$long_line" > "$TEST_DIR/long.log"
    run "$SCRIPT_DIR/check_config_errors.sh" "$TEST_DIR/long.log"
    [ "$status" -eq 0 ]
    rm -f "$TEST_DIR/long.log"
}
