#!/usr/bin/env bash

# Resource monitoring script for IOTA testing environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_INTERVAL=5  # seconds
OUTPUT_FILE="$SCRIPT_DIR/performance_results/resource_usage_$(date +%Y%m%d_%H%M%S).log"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Print header
echo "=== IOTA Resource Monitoring ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Output file: $OUTPUT_FILE"
echo "Monitoring interval: ${MONITOR_INTERVAL}s"
echo

# Function to validate metrics
validate_metric() {
    local metric_name="$1"
    local value="$2"
    local min="$3"
    local max="$4"

    if (( $(echo "$value < $min" | bc -l) )) || (( $(echo "$value > $max" | bc -l) )); then
        echo "WARNING: $metric_name value $value outside expected range [$min-$max]" >&2
        return 1
    fi
    return 0
}

# Function to get memory usage
get_memory_usage() {
    local mem
    if [[ "$(uname)" == "Darwin" ]]; then
        page_size=$(pagesize)
        mem=$(vm_stat | awk -v page_size="$page_size" '
            /Pages free/ {free=$3}
            /Pages active/ {active=$3}
            /Pages inactive/ {inactive=$3}
            /Pages speculative/ {speculative=$3}
            /Pages wired down/ {wired=$4}
            END {
                total=((free+active+inactive+speculative+wired)*page_size/1024/1024)
                printf "%.2f", total
            }')
    else
        mem=$(free -m | awk '/Mem:/ {printf "%.2f", $3}')
    fi

    # Validate memory (0.1 MB to 1TB in MB)
    validate_metric "Memory" "$mem" "0.1" "1048576" || mem="0"
    echo "$mem"
}

# Function to get CPU usage
get_cpu_usage() {
    local cpu
    if [[ "$(uname)" == "Darwin" ]]; then
        cpu=$(top -l 1 | grep "CPU usage" | awk '{printf "%.1f", $3}')
    else
        cpu=$(top -bn1 | grep "Cpu(s)" | awk '{printf "%.1f", $2}')
    fi

    # Validate CPU (0-100%)
    validate_metric "CPU" "$cpu" "0" "100" || cpu="0"
    echo "$cpu"
}

# Function to get disk usage
get_disk_usage() {
    local disk
    disk=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')

    # Validate disk (0-100%)
    validate_metric "Disk" "$disk" "0" "100" || disk="0"
    echo "$disk"
}

# Function to get process count
get_process_count() {
    local count
    count=$(pgrep -f "performance_test|check_config_errors" | wc -l)

    # Validate process count (0-1000 processes)
    validate_metric "Process count" "$count" "0" "1000" || count="0"
    echo "$count"
}

# Monitor resources
echo "Starting resource monitoring..."
echo "Press Ctrl+C to stop"
echo

{
    echo "timestamp,memory_mb,cpu_percent,disk_percent,process_count"
    while true; do
        timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        memory=$(get_memory_usage)
        cpu=$(get_cpu_usage)
        disk=$(get_disk_usage)
        procs=$(get_process_count)

        echo "$timestamp,$memory,$cpu,$disk,$procs"

        # Also print to terminal
        printf "\rMemory: %6.2f MB | CPU: %4.1f%% | Disk: %3d%% | Processes: %2d" \
            "$memory" "$cpu" "$disk" "$procs"

        sleep "$MONITOR_INTERVAL"
    done
} | tee "$OUTPUT_FILE"

# Note: This script runs until interrupted with Ctrl+C
# The trap ensures we get a newline after the script ends
trap 'echo' EXIT
