#!/usr/bin/env bash

# Integration test suite for IOTA configuration system
# Verifies interaction between components and system-wide functionality

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="$SCRIPT_DIR/integration_tests"
TEMP_DIR="$(mktemp -d)"
LOG_DIR="$TEST_DIR/logs"

# Ensure cleanup on exit
cleanup() {
    echo "Cleaning up test environment..."
    rm -rf "$TEMP_DIR"
    rm -f /tmp/test_*.lock
}
trap cleanup EXIT

# Utility functions
log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

error() {
    echo "ERROR: $*" >&2
    exit 1
}

check_dependencies() {
    local missing=()
    for cmd in jq bc curl mktemp; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing required dependencies: ${missing[*]}"
    fi
}

# Test functions
test_config_parser() {
    log "Testing config parser..."

    # Create test config
    cat > "$TEMP_DIR/test_config.json" <<EOF
{
    "app": "test",
    "version": "1.0",
    "logging": {
        "level": "INFO",
        "file": "/tmp/test.log"
    }
}
EOF

    # Test validation
    if ! "$ROOT_DIR/scripts/check_config_errors.sh" "$TEMP_DIR/test_config.json"; then
        error "Config parser validation failed"
    fi

    log "Config parser tests passed"
}

test_error_logger() {
    log "Testing error logger..."

    # Generate test errors
    for i in {1..5}; do
        echo "{\"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"level\": \"ERROR\", \"message\": \"Test error $i\"}" >> "$TEMP_DIR/test_errors.log"
    done

    # Test error processing
    if ! "$ROOT_DIR/scripts/check_config_errors.sh" "$TEMP_DIR/test_errors.log"; then
        error "Error logger processing failed"
    fi

    log "Error logger tests passed"
}

test_perf_monitor() {
    log "Testing performance monitor..."

    # Generate large test file
    for i in {1..1000}; do
        echo "{\"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"level\": \"INFO\", \"message\": \"Test entry $i\"}" >> "$TEMP_DIR/perf_test.log"
    done

    # Test performance
    if ! timeout 30s "$ROOT_DIR/scripts/check_config_errors.sh" "$TEMP_DIR/perf_test.log"; then
        error "Performance monitor test failed"
    fi

    log "Performance monitor tests passed"
}

# Main execution
main() {
    local component="${1:-}"

    # Create necessary directories
    mkdir -p "$TEST_DIR" "$LOG_DIR"

    # Check dependencies
    check_dependencies

    case "$component" in
        --basic)
            test_config_parser
            ;;
        --full)
            test_config_parser
            test_error_logger
            test_perf_monitor
            ;;
        --component=config_parser)
            test_config_parser
            ;;
        --component=error_logger)
            test_error_logger
            ;;
        --component=perf_monitor)
            test_perf_monitor
            ;;
        *)
            echo "Usage: $0 [--basic|--full|--component=<component_name>]"
            echo "Components: config_parser, error_logger, perf_monitor"
            exit 1
            ;;
    esac

    log "All specified tests completed successfully"
}

main "$@"
