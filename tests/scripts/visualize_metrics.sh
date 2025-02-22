#!/usr/bin/env bash

# Metric visualization script for IOTA monitoring
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/performance_results"
OUTPUT_DIR="$RESULTS_DIR/visualizations"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Function to generate ASCII bar chart
generate_bar_chart() {
    local title="$1"
    local data_file="$2"
    local value_column="$3"
    local max_width=50

    echo "=== $title ==="
    echo

    # Calculate max value for scaling
    local max_value
    max_value=$(awk -F',' -v col="$value_column" 'NR>1 {if($col>max) max=$col} END{print max}' "$data_file")

    # Generate bars
    awk -F',' -v col="$value_column" -v max="$max_value" -v width="$max_width" '
    NR>1 {
        value=$col
        scaled=int(value/max*width)
        printf "%s [", substr($1,12,8)  # Show time portion of timestamp
        for(i=0;i<scaled;i++) printf "#"
        for(i=scaled;i<width;i++) printf " "
        printf "] %.1f\n", value
    }' "$data_file"
    echo
}

# Function to generate trend line
generate_trend() {
    local title="$1"
    local data_file="$2"
    local value_column="$3"
    local window=5  # Moving average window

    echo "=== $title Trend ==="
    echo

    # Calculate moving average and print trend
    awk -F',' -v col="$value_column" -v window="$window" '
    function abs(x) {return x < 0 ? -x : x}
    NR>1 {
        values[NR]=$col
        sum+=$col
        if(NR>window) {
            sum-=values[NR-window]
            avg=sum/window

            # Determine trend symbol
            if(NR>(window+1)) {
                prev_avg=prev_sum/window
                if(abs(avg-prev_avg) < 0.1) symbol="→"
                else if(avg > prev_avg) symbol="↗"
                else symbol="↘"
            } else symbol="→"

            printf "%s %s %.1f\n", substr($1,12,8), symbol, avg
            prev_sum=sum
        }
    }' "$data_file"
    echo
}

echo "=== IOTA Metric Visualization ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

# Process recent resource logs
recent_log=$(find "$RESULTS_DIR" -type f -name "resource_usage_*.log" -mtime -1 | sort | tail -n 1)

if [[ -f "$recent_log" ]]; then
    echo "Analyzing log: $(basename "$recent_log")"
    echo

    # Generate visualizations
    generate_bar_chart "Memory Usage (MB)" "$recent_log" 2
    generate_trend "Memory Usage" "$recent_log" 2

    generate_bar_chart "CPU Usage (%)" "$recent_log" 3
    generate_trend "CPU Usage" "$recent_log" 3

    generate_bar_chart "Disk Usage (%)" "$recent_log" 4
    generate_trend "Disk Usage" "$recent_log" 4
else
    echo "No recent resource logs found"
fi

echo "Visualization complete."
