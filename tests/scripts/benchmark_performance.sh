#!/usr/bin/env bash

# IOTA Performance Benchmark Script (Non-blocking version)
# This script uses non-blocking I/O and proper process management
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/performance_results"
BENCHMARK_DIR="$RESULTS_DIR/benchmarks"
TEST_SIZES=(100 1000 5000)  # Reduced test sizes
TIMEOUT=300  # 5 minutes maximum
TEMP_DIR=$(mktemp -d)
PROGRESS_FILE="$TEMP_DIR/progress"
RESULT_FILE="$TEMP_DIR/result"
PID_FILE="$TEMP_DIR/pid"
METRICS_DIR="$TEMP_DIR/metrics"
ALERT_DIR="$TEMP_DIR/alerts"
mkdir -p "$METRICS_DIR" "$ALERT_DIR"

# Ensure directories exist
mkdir -p "$BENCHMARK_DIR"

# Cleanup function
cleanup() {
    local pids
    if [[ -f "$PID_FILE" ]]; then
        # Read PIDs without using mapfile
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "Terminating process $pid..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
    fi

    echo "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Function to update progress
update_progress() {
    echo "$*" >> "$PROGRESS_FILE"
}

# Function to show progress
show_progress() {
    local current=$1
    local total=$2
    local size=$3

    # Only show percentage for datasets > 1000
    if [ "$total" -gt 1000 ]; then
        local percent=$((current * 100 / total))
        printf "\rProgress: %d/%d records (%d%%) " "$current" "$total" "$percent"
    else
        printf "\rGenerated %d/%d records" "$current" "$total"
    fi
}

# Function to generate test data (non-blocking)
generate_test_data() {
    local size="$1"
    local output_file="$BENCHMARK_DIR/test_data_${size}.log"

    {
        echo "timestamp,memory_mb,cpu_percent,disk_percent,process_count"
        local current=0
        for ((i=1; i<=size; i++)); do
            echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ"),$(( RANDOM % 1000 + 500 )),$(( RANDOM % 100 )),$(( RANDOM % 100 )),$(( RANDOM % 10 ))"

            # Update progress every 100 records or on completion
            if ((i % 100 == 0)) || ((i == size)); then
                show_progress "$i" "$size" "$size"
            fi
        done
        echo # New line after progress
    } > "$output_file" &

    echo $! >> "$PID_FILE"
    wait $! || return 1
    echo "$output_file"
}

# Function to run command with timeout
run_with_timeout() {
    local timeout="$1"
    shift
    local cmd="$*"

    # Run command in background
    eval "$cmd" > "$RESULT_FILE" 2>&1 &
    local pid=$!
    echo "$pid" >> "$PID_FILE"

    local start_time=$(date +%s)
    local status=0

    while kill -0 "$pid" 2>/dev/null; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if ((elapsed >= timeout)); then
            echo "Command timed out after ${timeout}s: $cmd"
            kill -9 "$pid" 2>/dev/null || true
            status=124
            break
        fi

        # Show progress every 5 seconds
        if ((elapsed % 5 == 0)); then
            if [[ -f "$PROGRESS_FILE" ]]; then
                tail -n 1 "$PROGRESS_FILE"
            fi
        fi
        sleep 1
    done

    wait "$pid" 2>/dev/null || true
    cat "$RESULT_FILE"
    return "$status"
}

# Store metrics in JSON format
store_metrics() {
    local timestamp=$1
    local memory=$2
    local cpu=$3
    local disk=$4

    cat > "$METRICS_DIR/current_metrics.json" << EOF
{
    "timestamp": "$timestamp",
    "memory_mb": $memory,
    "cpu_percent": $cpu,
    "disk_percent": $disk
}
EOF

    # Store metrics persistently
    if command -v python3 >/dev/null 2>&1; then
        python3 ./store_metrics.py "$METRICS_DIR" "$METRICS_DIR/current_metrics.json"
    fi
}

# Show performance trends
show_trends() {
    if command -v python3 >/dev/null 2>&1; then
        python3 ./visualize_trends.py "$METRICS_DIR"
    fi
}

# Check for alerts
check_alerts() {
    if command -v python3 >/dev/null 2>&1; then
        python3 ./alert_manager.py "./alert_config.json" "$ALERT_DIR" "$METRICS_DIR/current_metrics.json"
    fi
}

# Function to measure system metrics (non-blocking)
measure_metrics() {
    {
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        local memory_mb
        local cpu_percent
        local disk_percent

        if [[ "$(uname)" == "Darwin" ]]; then
            # Get page size for accurate memory calculation
            page_size=$(pagesize)
            memory_info=$(vm_stat | awk -v page_size="$page_size" '
                /Pages free/ {free=$3}
                /Pages active/ {active=$3}
                /Pages inactive/ {inactive=$3}
                /Pages speculative/ {speculative=$3}
                /Pages wired down/ {wired=$4}
                END {
                    total=((free+active+inactive+speculative+wired)*page_size/1024/1024)
                    used=((active+wired)*page_size/1024/1024)
                    printf "%.2f %.1f", total, (used/total)*100
                }')
            memory_mb=$(echo "$memory_info" | cut -d' ' -f1)
            memory_percent=$(echo "$memory_info" | cut -d' ' -f2)

            cpu_percent=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | tr -d '%')
        else
            memory_mb=$(free -m | awk '/Mem:/ {print $3}')
            memory_percent=$(free -m | awk '/Mem:/ {printf "%.1f", $3/$2*100}')
            cpu_percent=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
        fi

        disk_percent=$(df -h . | awk 'NR==2 {gsub(/%/,"",$5); print $5}')

        printf "Memory: %.2f MB (%.1f%% used)\n" "$memory_mb" "$memory_percent"
        printf "CPU: %.1f%%\n" "$cpu_percent"
        printf "Disk: %d%%\n" "$disk_percent"

        # Store metrics for trend analysis
        store_metrics "$timestamp" "$memory_mb" "$cpu_percent" "$disk_percent"

        # Check for alerts
        check_alerts
    } > "$RESULT_FILE" &

    local pid=$!
    echo "$pid" >> "$PID_FILE"
    wait "$pid"
    cat "$RESULT_FILE"
}

echo "=== IOTA Performance Benchmark (Non-blocking) ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Test sizes: ${TEST_SIZES[*]}"
echo "Timeout: ${TIMEOUT}s"
echo

# Benchmark trend analysis
echo "=== Trend Analysis Performance ==="
for size in "${TEST_SIZES[@]}"; do
    echo
    echo "Dataset size: $size records"

    # Generate test data
    echo "Generating test data..."
    test_file=$(run_with_timeout 60 generate_test_data "$size")
    if [[ $? -eq 124 ]]; then
        echo "WARNING: Test data generation timed out for size $size"
        continue
    fi

    # Run trend analysis
    echo "Running trend analysis..."
    if ! run_with_timeout 60 "$SCRIPT_DIR/analyze_trends.sh"; then
        echo "WARNING: Trend analysis timed out for size $size"
        continue
    fi

    # Measure system impact
    echo "Measuring system metrics..."
    measure_metrics
    echo
done

# Log rotation benchmark
echo "=== Log Rotation Performance ==="
for size in "${TEST_SIZES[@]}"; do
    echo
    echo "Dataset size: $size records"

    # Generate test data
    echo "Generating test data..."
    test_file=$(run_with_timeout 60 generate_test_data "$size")
    if [[ $? -eq 124 ]]; then
        echo "WARNING: Test data generation timed out for size $size"
        continue
    fi

    # Run log rotation
    echo "Testing log rotation..."
    if ! run_with_timeout 30 "$SCRIPT_DIR/rotate_logs.sh"; then
        echo "WARNING: Log rotation timed out for size $size"
        continue
    fi

    # Measure compression
    if [[ -f "$test_file" ]]; then
        original_size=$(stat -f%z "$test_file")
        gzip -k "$test_file"
        compressed_size=$(stat -f%z "${test_file}.gz")
        compression_ratio=$(echo "scale=2; $original_size/$compressed_size" | bc)
        echo "Compression ratio: ${compression_ratio}x"
        rm -f "${test_file}.gz"
    fi

    # Measure system impact
    echo "Measuring system metrics..."
    measure_metrics
    echo
done

echo
echo "Benchmark complete."
echo "Results stored in: $BENCHMARK_DIR"

echo -e "\n=== Performance Trends ==="
show_trends
