#!/usr/bin/env python3
"""Run validation with test environment."""

import os
import subprocess
import sys
from typing import Dict


def run_validation(test_env: Dict[str, str]) -> bool:
    """Run validation script with test environment.

    Args:
        test_env: Dictionary of environment variables for testing

    Returns:
        bool: True if validation passed, False if failed

    Raises:
        RuntimeError: If subprocess execution fails
    """
    try:
        # Update environment
        env = os.environ.copy()
        env.update(test_env)

        # Run validation script
        result = subprocess.run(
            ["python", "scripts/validate_config.py"], env=env, capture_output=True, text=True
        )

        # Print output
        print(result.stdout)
        if result.stderr:
            print("Errors:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)

        return result.returncode == 0

    except subprocess.SubprocessError as e:
        raise RuntimeError(f"Failed to run validation: {e}")


def main():
    """Main entry point."""
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "testing",
        "SECRET_KEY": "this_is_a_very_secure_secret_key_for_testing_32",
        "DEBUG": "false",
        "ALLOWED_HOSTS": '["localhost", "127.0.0.1"]',
        "SENTRY_ENABLED": "false",
    }

    try:
        success = run_validation(test_env)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
