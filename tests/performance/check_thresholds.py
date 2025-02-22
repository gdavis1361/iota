#!/usr/bin/env python3
"""Check performance test results against thresholds."""
import argparse
import glob
import json
import sys
from typing import Dict, List

from bs4 import BeautifulSoup


def parse_locust_report(html_file: str) -> Dict:
    """Parse Locust HTML report."""
    with open(html_file, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Extract statistics table
    stats = {}
    stats_table = soup.find("table", {"class": "stats"})
    if stats_table:
        for row in stats_table.find_all("tr")[1:]:  # Skip header
            cols = row.find_all("td")
            if len(cols) >= 7:
                endpoint = cols[0].text.strip()
                stats[endpoint] = {
                    "requests": int(cols[1].text.strip()),
                    "failures": int(cols[2].text.strip()),
                    "median_response_time": float(cols[3].text.strip()),
                    "avg_response_time": float(cols[4].text.strip()),
                    "min_response_time": float(cols[5].text.strip()),
                    "max_response_time": float(cols[6].text.strip()),
                }

    # Extract percentiles
    percentiles = {}
    percentile_table = soup.find("table", {"class": "percentiles"})
    if percentile_table:
        for row in percentile_table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                endpoint = cols[0].text.strip()
                percentiles[endpoint] = {
                    "95th": float(cols[1].text.strip()),
                    "99th": float(cols[2].text.strip()),
                }

    return {"stats": stats, "percentiles": percentiles}


def check_thresholds(reports: List[Dict], config: Dict, redis_analysis: Dict) -> Dict:
    """Check performance results against thresholds."""
    results = {
        "violations": [],
        "warnings": [],
        "summary": {"total_checks": 0, "violations": 0, "warnings": 0},
    }

    thresholds = config["thresholds"]

    for report in reports:
        for endpoint, stats in report["stats"].items():
            results["summary"]["total_checks"] += 1

            # Check response times
            if endpoint in report["percentiles"]:
                p95 = report["percentiles"][endpoint]["95th"]
                p99 = report["percentiles"][endpoint]["99th"]

                if p95 > thresholds["response_time_95th_percentile"]:
                    results["violations"].append(
                        {
                            "type": "response_time_95th",
                            "endpoint": endpoint,
                            "value": p95,
                            "threshold": thresholds["response_time_95th_percentile"],
                            "message": f"95th percentile response time exceeded for {endpoint}",
                        }
                    )

                if p99 > thresholds["response_time_99th_percentile"]:
                    results["violations"].append(
                        {
                            "type": "response_time_99th",
                            "endpoint": endpoint,
                            "value": p99,
                            "threshold": thresholds["response_time_99th_percentile"],
                            "message": f"99th percentile response time exceeded for {endpoint}",
                        }
                    )

            # Check error rate
            if stats["requests"] > 0:
                error_rate = (stats["failures"] / stats["requests"]) * 100
                if error_rate > thresholds["error_rate"]:
                    results["violations"].append(
                        {
                            "type": "error_rate",
                            "endpoint": endpoint,
                            "value": error_rate,
                            "threshold": thresholds["error_rate"],
                            "message": f"Error rate exceeded for {endpoint}",
                        }
                    )

    # Check Redis analysis
    if redis_analysis["summary"]["threshold_violations"] > 0:
        for violation in redis_analysis["violations"]:
            results["violations"].append(
                {
                    "type": "redis",
                    "value": violation["value"],
                    "threshold": violation["threshold"],
                    "message": violation["message"],
                }
            )

    # Add Redis recommendations as warnings
    for recommendation in redis_analysis.get("recommendations", []):
        results["warnings"].append({"type": "redis_recommendation", "message": recommendation})

    results["summary"]["violations"] = len(results["violations"])
    results["summary"]["warnings"] = len(results["warnings"])

    return results


def main():
    parser = argparse.ArgumentParser(description="Check performance thresholds")
    parser.add_argument("--config", required=True, help="Load test configuration file")
    parser.add_argument("--reports", required=True, help="Glob pattern for Locust HTML reports")
    parser.add_argument("--redis-analysis", required=True, help="Redis analysis JSON file")

    args = parser.parse_args()

    try:
        # Load configuration
        with open(args.config, "r") as f:
            config = json.load(f)

        # Load Redis analysis
        with open(args.redis_analysis, "r") as f:
            redis_analysis = json.load(f)

        # Parse all reports
        reports = []
        for report_file in glob.glob(args.reports):
            reports.append(parse_locust_report(report_file))

        # Check thresholds
        results = check_thresholds(reports, config, redis_analysis)

        # Print results
        print(f"\nPerformance Threshold Check Results:")
        print(f"Total checks: {results['summary']['total_checks']}")
        print(f"Violations: {results['summary']['violations']}")
        print(f"Warnings: {results['summary']['warnings']}")

        if results["violations"]:
            print("\nViolations:")
            for violation in results["violations"]:
                print(f"- {violation['message']}")

        if results["warnings"]:
            print("\nWarnings:")
            for warning in results["warnings"]:
                print(f"- {warning['message']}")

        # Exit with error if violations found
        sys.exit(1 if results["violations"] else 0)

    except Exception as e:
        print(f"Error checking performance thresholds: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
