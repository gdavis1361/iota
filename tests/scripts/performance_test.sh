#!/usr/bin/env bash

# Fail on any error, undefined variable, or pipe failure
set -euo pipefail

# Debug: Print script startup information
echo "=== Performance Test Script Starting ==="
echo "Command line arguments: $*"
echo "Current directory: $(pwd)"
echo "Script location: $0"
echo

# Constants
SMALL_DATASET=10
MEDIUM_DATASET=100
LARGE_DATASET=1000

# Check for validation flag
IS_VALIDATION=false
if [[ "${1:-}" == "--validate" ]]; then
    IS_VALIDATION=true
    echo "Validation mode activated"
    echo "Will run single test with $SMALL_DATASET entries"
fi

# Basic system information
echo "=== System Information ==="
echo "OS: $(uname -s)"
echo "Kernel: $(uname -r)"
echo "Shell: $SHELL"
echo "Bash Version: ${BASH_VERSION}"
echo

# Function to run a single test
run_single_test() {
    local size=$1
    local desc=$2

    echo "=== Running Test: $desc ==="
    echo "Dataset size: $size entries"
    echo "Start time: $(date)"

    # Generate test data
    local test_file=$(mktemp)
    echo "Generated test file: $test_file"

    # Create sample data
    for ((i=1; i<=size; i++)); do
        echo "Test entry $i" >> "$test_file"
    done

    # Run the actual test
    echo "Processing test file..."
    wc -l "$test_file"

    # Cleanup
    rm -f "$test_file"
    echo "Test complete: $(date)"
    echo
}

# Main execution
if [[ "$IS_VALIDATION" == "true" ]]; then
    echo "=== Starting Validation Test ==="
    run_single_test "$SMALL_DATASET" "Validation"
    echo "=== Validation Test Complete ==="
    exit 0
else
    echo "=== Starting Full Test Suite ==="
    run_single_test "$SMALL_DATASET" "Small Dataset"
    run_single_test "$MEDIUM_DATASET" "Medium Dataset"
    run_single_test "$LARGE_DATASET" "Large Dataset"
    echo "=== Full Test Suite Complete ==="
fi
