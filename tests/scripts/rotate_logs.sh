#!/usr/bin/env bash

# Log rotation script for IOTA testing environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/performance_results"
MAX_LOG_AGE_DAYS=7
MAX_LOG_SIZE_MB=100
COMPRESS_LOGS=true

# Print header
echo "=== IOTA Log Rotation ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Function to compress old logs
compress_old_logs() {
    local log_file="$1"
    if [[ "$COMPRESS_LOGS" == "true" && ! "$log_file" =~ \.gz$ ]]; then
        echo "Compressing: $log_file"
        gzip "$log_file"
    fi
}

# Function to get file size in MB
get_file_size_mb() {
    local file="$1"
    if [[ "$(uname)" == "Darwin" ]]; then
        stat -f%z "$file" | awk '{printf "%.2f", $1/1024/1024}'
    else
        stat -c%s "$file" | awk '{printf "%.2f", $1/1024/1024}'
    fi
}

echo "Starting log rotation..."
echo "- Max age: $MAX_LOG_AGE_DAYS days"
echo "- Max size: $MAX_LOG_SIZE_MB MB"
echo "- Compression: $COMPRESS_LOGS"
echo

# Rotate old logs
find "$RESULTS_DIR" -type f -name "*.log" -mtime +"$MAX_LOG_AGE_DAYS" | while read -r log_file; do
    echo "Rotating old log: $log_file"
    compress_old_logs "$log_file"
done

# Rotate large logs
find "$RESULTS_DIR" -type f -name "*.log" | while read -r log_file; do
    size_mb=$(get_file_size_mb "$log_file")
    if (( $(echo "$size_mb > $MAX_LOG_SIZE_MB" | bc -l) )); then
        echo "Rotating large log: $log_file ($size_mb MB)"
        compress_old_logs "$log_file"
    fi
done

# Clean up old compressed logs (>30 days)
find "$RESULTS_DIR" -type f -name "*.log.gz" -mtime +30 -delete

echo
echo "Log rotation complete."
echo "Current log directory size: $(du -sh "$RESULTS_DIR" | cut -f1)"
