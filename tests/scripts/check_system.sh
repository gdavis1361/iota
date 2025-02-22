#!/usr/bin/env bash

# System status check script for IOTA testing environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print header
echo "=== IOTA System Status Check ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

# System information
echo "=== System Information ==="
echo "OS: $(uname -s)"
echo "Kernel: $(uname -r)"
echo "Machine: $(uname -m)"
echo

# Memory status
echo "=== Memory Status ==="
if [[ "$(uname)" == "Darwin" ]]; then
    # Get page size and vm_stat output
    page_size=$(pagesize)
    vm_stat | awk -v page_size="$page_size" '
        /Pages free/ {free=$3}
        /Pages active/ {active=$3}
        /Pages inactive/ {inactive=$3}
        /Pages speculative/ {speculative=$3}
        /Pages wired down/ {wired=$4}
        END {
            # Convert page counts to GB, removing trailing period
            total=((free+active+inactive+speculative+wired)*page_size/1024/1024/1024)
            used=((active+wired)*page_size/1024/1024/1024)
            printf "Total Memory: %.2f GB\n", total
            printf "Used Memory: %.2f GB (%.1f%%)\n", used, (used/total)*100
        }'
else
    free -h
fi
echo

# Disk space
echo "=== Disk Space ==="
df -h .
echo

# Process status
echo "=== Process Status ==="
ps aux | grep -E "performance_test|check_config_errors" | grep -v grep || echo "No test processes running"
echo

# Check dependencies
echo "=== Dependencies ==="
for cmd in jq bc curl mktemp; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "✓ $cmd installed"
    else
        echo "✗ $cmd missing"
    fi
done
echo

# Check test directories
echo "=== Test Directories ==="
for dir in "$SCRIPT_DIR" "$SCRIPT_DIR/../scripts" "$SCRIPT_DIR/performance_results"; do
    if [[ -d "$dir" ]]; then
        echo "✓ $dir exists"
    else
        echo "✗ $dir missing"
    fi
done
echo

# Check file permissions
echo "=== Script Permissions ==="
for script in "$SCRIPT_DIR"/*.sh; do
    if [[ -x "$script" ]]; then
        echo "✓ $(basename "$script") is executable"
    else
        echo "✗ $(basename "$script") not executable"
    fi
done
echo

# Check for lock files
echo "=== Lock Files ==="
if ls /tmp/test_*.lock >/dev/null 2>&1; then
    echo "! Lock files found:"
    ls -l /tmp/test_*.lock
else
    echo "✓ No lock files present"
fi
echo

echo "System check complete."
