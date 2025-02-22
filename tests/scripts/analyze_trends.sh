#!/usr/bin/env bash

# Trend analysis script for IOTA testing environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/performance_results"
ANALYSIS_PERIOD_DAYS=7

# Print header
echo "=== IOTA Trend Analysis ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Analysis period: $ANALYSIS_PERIOD_DAYS days"
echo

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Function to calculate statistics
calculate_stats() {
    awk '
    BEGIN {
        min=999999; max=-999999; sum=0; count=0
    }
    NR>1 { # Skip header
        if($1 < min) min=$1
        if($1 > max) max=$1
        sum+=$1; count++
    }
    END {
        if(count>0) {
            avg=sum/count
            printf "%.2f,%.2f,%.2f,%.2f,%d", min, max, avg, (max-min), count
        }
    }'
}

echo "Analyzing performance trends..."
echo

# Process resource logs
echo "=== Resource Usage Trends ==="
echo "Metric,Min,Max,Avg,Range,Samples"
for metric in memory_mb cpu_percent disk_percent process_count; do
    echo -n "$metric,"
    find "$RESULTS_DIR" -type f -name "resource_usage_*.log" -mtime -"$ANALYSIS_PERIOD_DAYS" \
        -exec awk -F',' -v col="$metric" '
            NR==1 {
                for(i=1;i<=NF;i++) {
                    if($i==col) {target_col=i; exit}
                }
            }
            NR>1 {print $target_col}
        ' {} \; | calculate_stats
    echo
done

# Process test completion times
echo
echo "=== Test Completion Time Trends ==="
echo "Test Type,Min (s),Max (s),Avg (s),Range (s),Count"
grep -h "test.*complete" "$RESULTS_DIR"/*.log | \
    awk '{print $NF}' | \
    calculate_stats | \
    awk -F',' '{printf "Integration,%s\n", $0}'

# Calculate success rates
echo
echo "=== Test Success Rate Trends ==="
total_tests=$(find "$RESULTS_DIR" -type f -name "*.log" -mtime -"$ANALYSIS_PERIOD_DAYS" | wc -l)
successful_tests=$(find "$RESULTS_DIR" -type f -name "*.log" -mtime -"$ANALYSIS_PERIOD_DAYS" -exec grep -l "test.*complete" {} \; | wc -l)
if [[ $total_tests -gt 0 ]]; then
    success_rate=$(( successful_tests * 100 / total_tests ))
    echo "Success Rate: $success_rate% ($successful_tests/$total_tests tests)"
fi

# Error pattern analysis
echo
echo "=== Error Pattern Trends ==="
echo "Top error patterns in the last $ANALYSIS_PERIOD_DAYS days:"
find "$RESULTS_DIR" -type f -name "*.log" -mtime -"$ANALYSIS_PERIOD_DAYS" \
    -exec grep -h "ERROR:" {} \; | \
    sort | uniq -c | sort -nr | head -5

# Performance regression analysis
echo
echo "=== Performance Regression Analysis ==="
latest_avg=$(find "$RESULTS_DIR" -type f -name "resource_usage_*.log" -mtime -1 \
    -exec awk -F',' 'NR>1{sum+=$2; count++} END{if(count>0) printf "%.2f", sum/count}' {} \;)
week_avg=$(find "$RESULTS_DIR" -type f -name "resource_usage_*.log" -mtime -"$ANALYSIS_PERIOD_DAYS" \
    -exec awk -F',' 'NR>1{sum+=$2; count++} END{if(count>0) printf "%.2f", sum/count}' {} \;)

if [[ -n "$latest_avg" && -n "$week_avg" ]]; then
    echo "Memory usage trend:"
    echo "- Last 24h average: $latest_avg MB"
    echo "- $ANALYSIS_PERIOD_DAYS-day average: $week_avg MB"

    # Calculate percentage change
    if (( $(echo "$week_avg > 0" | bc -l) )); then
        change=$(echo "scale=2; ($latest_avg - $week_avg) * 100 / $week_avg" | bc)
        echo "- Change: $change%"
    fi
fi

echo
echo "Trend analysis complete."
