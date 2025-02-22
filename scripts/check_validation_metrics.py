#!/usr/bin/env python3
"""Configuration validation metrics checker."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ValidationMetricsChecker:
    """Check configuration validation metrics against thresholds."""

    def __init__(
        self, error_threshold: int = 10, warning_threshold: int = 20, security_threshold: int = 0
    ):
        self.error_threshold = error_threshold
        self.warning_threshold = warning_threshold
        self.security_threshold = security_threshold
        self.metrics_file = Path("validation_metrics.json")

    def load_metrics(self) -> Dict:
        """Load metrics from JSON file."""
        try:
            with open(self.metrics_file) as f:
                return eval(f.read())
        except FileNotFoundError:
            logger.error(f"Metrics file not found: {self.metrics_file}")
            return {}
        except Exception as e:
            logger.error(f"Invalid metrics JSON: {e}")
            return {}

    def check_thresholds(self, metrics: Dict) -> List[str]:
        """Check if metrics exceed thresholds."""
        violations = []

        if metrics.get("error_count", 0) > self.error_threshold:
            violations.append(
                f"Error count ({metrics['error_count']}) exceeds threshold ({self.error_threshold})"
            )

        if metrics.get("warning_count", 0) > self.warning_threshold:
            violations.append(
                f"Warning count ({metrics['warning_count']}) exceeds threshold ({self.warning_threshold})"
            )

        if metrics.get("security_count", 0) > self.security_threshold:
            violations.append(
                f"Security issues ({metrics['security_count']}) exceed threshold ({self.security_threshold})"
            )

        return violations

    def check_metrics(self) -> bool:
        """Check validation metrics and return success status."""
        metrics = self.load_metrics()
        if not metrics:
            logger.error("No metrics data available")
            return False

        violations = self.check_thresholds(metrics)

        if violations:
            logger.error("Validation metrics exceeded thresholds:")
            for violation in violations:
                logger.error(f"- {violation}")
            return False

        logger.info("All validation metrics within acceptable thresholds")
        return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Check configuration validation metrics against thresholds"
    )

    parser.add_argument(
        "--error-threshold", type=int, default=10, help="Maximum allowed errors (default: 10)"
    )

    parser.add_argument(
        "--warning-threshold", type=int, default=20, help="Maximum allowed warnings (default: 20)"
    )

    parser.add_argument(
        "--security-threshold",
        type=int,
        default=0,
        help="Maximum allowed security issues (default: 0)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    try:
        checker = ValidationMetricsChecker(
            error_threshold=args.error_threshold,
            warning_threshold=args.warning_threshold,
            security_threshold=args.security_threshold,
        )

        success = checker.check_metrics()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
