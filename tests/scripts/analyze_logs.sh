#!/usr/bin/env bash

# Log analysis script for IOTA testing environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/performance_results"

# Print header
echo "=== IOTA Log Analysis ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

# Check if results directory exists
if [[ ! -d "$RESULTS_DIR" ]]; then
    echo "Error: Results directory not found: $RESULTS_DIR"
    exit 1
fi

# Analyze performance test logs
echo "=== Performance Test Analysis ==="
echo "Last 24 hours of test results:"
find "$RESULTS_DIR" -type f -name "*.log" -mtime -1 -exec sh -c '
    echo "File: $(basename "$1")"
    echo "- Size: $(wc -c < "$1" | numfmt --to=iec-i --suffix=B)"
    echo "- Lines: $(wc -l < "$1")"
    echo "- Created: $(stat -f "%Sm" "$1")"
    echo "- Test result: $(grep -l "test.*complete" "$1" > /dev/null && echo "✓ Complete" || echo "✗ Incomplete")"
    echo
' sh {} \;

# Error pattern analysis
echo "=== Error Pattern Analysis ==="
echo "Common error patterns found:"
find "$RESULTS_DIR" -type f -name "*.log" -exec grep -h "ERROR:" {} \; | sort | uniq -c | sort -nr

# Performance metrics
echo
echo "=== Performance Metrics ==="
echo "Average execution times:"
find "$RESULTS_DIR" -type f -name "*.log" -exec grep -h "Execution time:" {} \; | \
    awk '{ sum += $3; count++ } END { if (count > 0) printf "%.2f seconds\n", sum/count }'

# Resource usage patterns
echo
echo "=== Resource Usage Patterns ==="
echo "Memory usage distribution:"
find "$RESULTS_DIR" -type f -name "*.log" -exec grep -h "Memory usage:" {} \; | \
    awk '{ sum += $3; count++ } END { if (count > 0) printf "Average: %.2f KB\n", sum/count }'

# Test completion status
echo
echo "=== Test Completion Status ==="
total_tests=$(find "$RESULTS_DIR" -type f -name "*.log" | wc -l)
completed_tests=$(find "$RESULTS_DIR" -type f -name "*.log" -exec grep -l "test.*complete" {} \; | wc -l)
echo "Total tests: $total_tests"
echo "Completed tests: $completed_tests"
if [[ $total_tests -gt 0 ]]; then
    completion_rate=$(( completed_tests * 100 / total_tests ))
    echo "Completion rate: $completion_rate%"
fi

# Summary
echo
echo "=== Analysis Summary ==="
echo "- Total log files: $total_tests"
echo "- Recent tests (24h): $(find "$RESULTS_DIR" -type f -name "*.log" -mtime -1 | wc -l)"
echo "- Completion rate: $completion_rate%"
echo "- Most common errors: $(find "$RESULTS_DIR" -type f -name "*.log" -exec grep -h "ERROR:" {} \; | sort | uniq -c | sort -nr | head -1)"

echo
echo "Log analysis complete."
