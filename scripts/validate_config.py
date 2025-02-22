#!/usr/bin/env python3
"""Configuration validation script for CI/CD pipeline."""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from server.core.config import Settings, get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConfigurationValidator:
    """Validates application configuration and checks for security issues."""

    def __init__(self):
        self.settings: Optional[Settings] = None
        self.issues: Dict[str, Any] = {"errors": [], "warnings": [], "security_concerns": []}

    def validate_settings(self) -> bool:
        """Validate all settings and collect any issues."""
        try:
            self.settings = get_settings()
            return self._run_validations()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self.issues["errors"].append(f"Configuration error: {e}")
            return False

    def _run_validations(self) -> bool:
        """Run all validation checks."""
        checks = [
            self._validate_security_settings,
            self._validate_environment,
            self._validate_sentry_config,
            self._check_secret_age,
            self._validate_allowed_hosts,
        ]

        success = True
        for check in checks:
            try:
                success = check() and success
            except Exception as e:
                logger.error(f"Validation check failed: {e}")
                self.issues["errors"].append(f"Validation error: {e}")
                success = False

        return success

    def _validate_security_settings(self) -> bool:
        """Validate security-related settings."""
        try:
            self.settings = get_settings()  # Refresh settings
            secret_key = self.settings.SECRET_KEY.get_secret_value()
            if len(secret_key) < 32:
                self.issues["security_concerns"].append(
                    "SECRET_KEY is too short (should be at least 32 characters)"
                )
                return False
            return True
        except ValueError as e:
            # Handle Pydantic validation errors
            self.issues["errors"].append(str(e))
            return False
        except Exception as e:
            self.issues["errors"].append(f"Failed to validate SECRET_KEY: {e}")
            return False

    def _validate_environment(self) -> bool:
        """Validate environment-specific settings."""
        try:
            self.settings = get_settings()  # Refresh settings
            valid_environments = {"development", "staging", "production", "test"}
            env = self.settings.ENVIRONMENT.lower()

            if env not in valid_environments:
                self.issues["errors"].append(
                    f"Invalid ENVIRONMENT value. Must be one of: {', '.join(valid_environments)}"
                )
                return False

            if env == "production" and self.settings.DEBUG:
                self.issues["security_concerns"].append("DEBUG should not be enabled in production")
                return False

            return True
        except ValueError as e:
            # Handle Pydantic validation errors
            self.issues["errors"].append(str(e))
            return False
        except Exception as e:
            self.issues["errors"].append(f"Failed to validate environment: {e}")
            return False

    def _validate_sentry_config(self) -> bool:
        """Validate Sentry configuration."""
        try:
            self.settings = get_settings()  # Refresh settings
            if not self.settings.SENTRY_ENABLED:
                return True

            if not self.settings.SENTRY_DSN:
                self.issues["errors"].append("SENTRY_DSN is required when Sentry is enabled")
                return False

            if self.settings.SENTRY_DSN:
                dsn = self.settings.SENTRY_DSN
                if not dsn.startswith(("http://", "https://")):
                    self.issues["errors"].append("SENTRY_DSN must start with http:// or https://")
                    return False

                if self.settings.SENTRY_ENVIRONMENT != self.settings.ENVIRONMENT:
                    self.issues["warnings"].append(
                        "SENTRY_ENVIRONMENT differs from application ENVIRONMENT"
                    )

            return True
        except ValueError as e:
            # Handle Pydantic validation errors
            self.issues["errors"].append(str(e))
            return False
        except Exception as e:
            self.issues["errors"].append(f"Failed to validate Sentry configuration: {e}")
            return False

    def _check_secret_age(self) -> bool:
        """Check if secrets might need rotation."""
        # This is a placeholder for secret age checking
        # In a real implementation, you would track secret creation time
        return True

    def _validate_allowed_hosts(self) -> bool:
        """Validate allowed hosts configuration."""
        try:
            self.settings = get_settings()  # Refresh settings
            if "*" in self.settings.ALLOWED_HOSTS:
                if self.settings.ENVIRONMENT == "production":
                    self.issues["security_concerns"].append(
                        "Wildcard ALLOWED_HOSTS should not be used in production"
                    )
                    return False
                else:
                    self.issues["warnings"].append(
                        "Using wildcard ALLOWED_HOSTS - consider restricting this"
                    )

            return True
        except ValueError as e:
            # Handle Pydantic validation errors
            self.issues["errors"].append(str(e))
            return False
        except Exception as e:
            self.issues["errors"].append(f"Failed to validate allowed hosts: {e}")
            return False

    def print_report(self):
        """Print validation report."""
        print("\nConfiguration Validation Report")
        print("==============================")

        if not any(self.issues.values()):
            print("✅ All validations passed successfully!")
            return

        for category, items in self.issues.items():
            if items:
                print(f"\n{category.upper()}:")
                for item in items:
                    print(f"- {item}")


def main():
    """Main entry point for configuration validation."""
    validator = ConfigurationValidator()
    success = validator.validate_settings()

    validator.print_report()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
