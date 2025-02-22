#!/usr/bin/env bash

# Alert monitoring script for IOTA
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/performance_results"
CONFIG_FILE="$SCRIPT_DIR/alert_config.json"
ALERT_LOG="$RESULTS_DIR/alerts.log"
ALERT_STATE_FILE="$RESULTS_DIR/.alert_state"

# Ensure directories exist
mkdir -p "$RESULTS_DIR"

# Function to read config values
get_config() {
    local path="$1"
    jq -r "$path" "$CONFIG_FILE"
}

# Function to check if we should throttle alerts
should_throttle() {
    local alert_type="$1"
    local current_time
    current_time=$(date +%s)

    # Read throttle config
    local throttle_period
    throttle_period=$(get_config '.notification.throttle.period')
    local max_alerts
    max_alerts=$(get_config '.notification.throttle.max_alerts')

    # Check if state file exists
    if [[ -f "$ALERT_STATE_FILE" ]]; then
        # Count recent alerts
        local recent_alerts
        recent_alerts=$(awk -v now="$current_time" -v period="$throttle_period" -v type="$alert_type" \
            '$1 >= (now-period) && $2 == type {count++} END{print count}' "$ALERT_STATE_FILE")

        if (( recent_alerts >= max_alerts )); then
            return 0  # Should throttle
        fi
    fi
    return 1  # Should not throttle
}

# Function to record alert
record_alert() {
    local alert_type="$1"
    local message="$2"
    local severity="$3"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Record alert state
    echo "$(date +%s) $alert_type $severity" >> "$ALERT_STATE_FILE"

    # Log alert
    echo "[$timestamp] $severity - $alert_type: $message" >> "$ALERT_LOG"

    # Output to stdout if configured
    if [[ $(get_config '.notification.methods | contains(["stdout"])') == "true" ]]; then
        echo "[$timestamp] $severity - $alert_type: $message"
    fi
}

# Function to check metric against thresholds
check_metric() {
    local type="$1"
    local value="$2"
    local warning_threshold
    warning_threshold=$(get_config ".alerts.$type.warning_threshold")
    local critical_threshold
    critical_threshold=$(get_config ".alerts.$type.critical_threshold")

    if (( $(echo "$value >= $critical_threshold" | bc -l) )); then
        if ! should_throttle "$type"; then
            record_alert "$type" "Value $value exceeds critical threshold $critical_threshold" "CRITICAL"
        fi
    elif (( $(echo "$value >= $warning_threshold" | bc -l) )); then
        if ! should_throttle "$type"; then
            record_alert "$type" "Value $value exceeds warning threshold $warning_threshold" "WARNING"
        fi
    fi
}

# Main monitoring loop
echo "=== IOTA Alert Monitor ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Config: $CONFIG_FILE"
echo "Alert log: $ALERT_LOG"
echo

while true; do
    # Get current metrics
    memory_usage=$("$SCRIPT_DIR/check_system.sh" | awk '/Used Memory/ {sub(/%/,"",$4); print $4}')
    cpu_usage=$("$SCRIPT_DIR/monitor_resources.sh" | awk -F',' 'NR>1 {print $3; exit}')
    disk_usage=$("$SCRIPT_DIR/monitor_resources.sh" | awk -F',' 'NR>1 {print $4; exit}')
    process_count=$("$SCRIPT_DIR/monitor_resources.sh" | awk -F',' 'NR>1 {print $5; exit}')

    # Check each metric
    check_metric "memory" "$memory_usage"
    check_metric "cpu" "$cpu_usage"
    check_metric "disk" "$disk_usage"
    check_metric "process_count" "$process_count"

    # Clean up old state entries
    if [[ -f "$ALERT_STATE_FILE" ]]; then
        threshold_time=$(($(date +%s) - $(get_config '.notification.throttle.period')))
        tmp_file=$(mktemp)
        awk -v threshold="$threshold_time" '$1 >= threshold' "$ALERT_STATE_FILE" > "$tmp_file"
        mv "$tmp_file" "$ALERT_STATE_FILE"
    fi

    sleep 60  # Check every minute
done
