#!/usr/bin/env python3
"""
IOTA Performance Trend Visualization Module
Processes benchmark metrics and generates ASCII-based visualizations
"""

import json
import os
import statistics
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class MetricVisualizer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.width = 60  # Default chart width
        self.height = 10  # Default chart height

    def load_metrics(self, days: int = 7) -> Dict[str, List[float]]:
        """Load metrics from the last N days"""
        metrics = {"memory_mb": [], "cpu_percent": [], "disk_percent": [], "process_count": []}

        cutoff = datetime.now() - timedelta(days=days)

        for filename in os.listdir(self.data_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.data_dir, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                if timestamp < cutoff:
                    continue

                for metric in metrics:
                    if metric in data:
                        metrics[metric].append(float(data[metric]))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Error processing {filename}: {e}", file=sys.stderr)

        return metrics

    def generate_sparkline(self, values: List[float], width: int = None) -> str:
        """Generate ASCII sparkline for a series of values"""
        if not values:
            return "No data"

        width = width or self.width
        blocks = "▁▂▃▄▅▆▇█"

        # Normalize values to 0-7 range for 8 blocks
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val

        if range_val == 0:
            return blocks[0] * width

        # Sample values to fit width
        step = max(1, len(values) // width)
        sampled = values[::step][:width]

        return "".join(blocks[min(7, int(7 * (v - min_val) / range_val))] for v in sampled)

    def generate_summary_stats(self, values: List[float]) -> Dict[str, float]:
        """Generate summary statistics for a metric"""
        if not values:
            return {"min": 0, "max": 0, "avg": 0, "median": 0}

        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
        }

    def visualize_metrics(self, days: int = 7) -> str:
        """Generate a complete visualization of all metrics"""
        metrics = self.load_metrics(days)
        output = []

        output.append("=== IOTA Performance Trends ===")
        output.append(f"Period: Last {days} days")
        output.append("")

        for metric_name, values in metrics.items():
            if not values:
                continue

            stats = self.generate_summary_stats(values)
            sparkline = self.generate_sparkline(values)

            output.append(f"=== {metric_name.replace('_', ' ').title()} ===")
            output.append(sparkline)
            output.append(f"Min: {stats['min']:.2f}")
            output.append(f"Max: {stats['max']:.2f}")
            output.append(f"Avg: {stats['avg']:.2f}")
            output.append(f"Median: {stats['median']:.2f}")
            output.append("")

        return "\n".join(output)


def main():
    if len(sys.argv) != 2:
        print("Usage: visualize_trends.py <metrics_directory>", file=sys.stderr)
        sys.exit(1)

    data_dir = sys.argv[1]
    if not os.path.isdir(data_dir):
        print(f"Error: {data_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    visualizer = MetricVisualizer(data_dir)
    print(visualizer.visualize_metrics())


if __name__ == "__main__":
    main()
