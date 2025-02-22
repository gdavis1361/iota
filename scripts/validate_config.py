#!/usr/bin/env python3
"""Configuration validation script for CI/CD pipeline."""
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ValidationRule(BaseModel):
    """Base validation rule model."""

    enabled: bool = True
    error_message: str
    severity: str = "error"  # error, warning, security


class LengthRule(ValidationRule):
    """Length validation rule."""

    min_length: int
    validation_type: str = "length"


class FormatRule(ValidationRule):
    """Format validation rule."""

    format: str
    validation_type: str = "format"


class ConditionalRule(ValidationRule):
    """Conditional validation rule."""

    condition: str
    validation_type: str = "conditional"


class ValidationMetrics(BaseModel):
    """Validation metrics model."""

    error_count: int = 0
    warning_count: int = 0
    security_count: int = 0
    validation_time_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    security_concerns: List[str] = Field(default_factory=list)
    last_validation: str = ""


class TemplateConfigValidator:
    """Validates template configuration rules."""

    def __init__(self):
        self.issues: Dict[str, List[str]] = {"errors": [], "warnings": [], "security_concerns": []}
        self.metrics = ValidationMetrics()
        self.rules = self.load_validation_rules()
        self.start_time = time.time()

    def load_validation_rules(self) -> Dict:
        """Load validation rules from YAML file."""
        try:
            rules_path = Path("config/validation_rules.yaml")
            if not rules_path.exists():
                raise FileNotFoundError("Validation rules file not found")

            with open(rules_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load validation rules: {e}")
            return {}

    def validate_settings(self) -> bool:
        """Validate all configuration settings."""
        try:
            self.start_time = time.time()

            valid_env = self._validate_environment()
            valid_security = self._validate_security_settings()
            valid_sentry = self._validate_sentry_config()
            valid_hosts = self._validate_allowed_hosts()

            self._update_metrics()
            return all([valid_env, valid_security, valid_sentry, valid_hosts])
        except Exception as e:
            logger.error(f"Failed to validate settings: {e}")
            self.issues["errors"].append(f"Settings validation error: {e}")
            self._update_metrics()
            return False

    def _validate_environment(self) -> bool:
        """Validate environment settings."""
        if not self.rules.get("validation_rules", {}).get("environment", {}).get("enabled", True):
            return True

        env_rules = self.rules["validation_rules"]["environment"]
        env = os.getenv("ENVIRONMENT", "").lower()

        if env not in env_rules["allowed_values"]:
            self.issues["errors"].append(env_rules["error_message"].format(value=env))
            return False

        # Check production rules
        if env == "production":
            for rule in env_rules.get("production_rules", []):
                if rule["rule"] == "debug_disabled" and os.getenv("DEBUG", "").lower() == "true":
                    self.issues["security_concerns"].append(rule["error_message"])
                    return False

        return True

    def _validate_security_settings(self) -> bool:
        """Validate security-related settings."""
        if (
            not self.rules.get("validation_rules", {})
            .get("security", {})
            .get("secret_key", {})
            .get("enabled", True)
        ):
            return True

        secret_key_rules = self.rules["validation_rules"]["security"]["secret_key"]
        secret_key = os.getenv("SECRET_KEY", "")

        if len(secret_key) < secret_key_rules["min_length"]:
            self.issues["security_concerns"].append(secret_key_rules["error_message"])
            return False

        return True

    def _validate_sentry_config(self) -> bool:
        """Validate Sentry configuration."""
        if not self.rules.get("validation_rules", {}).get("sentry", {}).get("enabled", True):
            return True

        sentry_rules = self.rules["validation_rules"]["sentry"]["rules"]
        sentry_enabled = os.getenv("SENTRY_ENABLED", "").lower() == "true"

        if not sentry_enabled:
            return True

        sentry_dsn = os.getenv("SENTRY_DSN")

        # Check DSN presence
        dsn_required_rule = next(r for r in sentry_rules if r["rule"] == "dsn_required_if_enabled")
        if not sentry_dsn:
            self.issues["errors"].append(dsn_required_rule["error_message"])
            return False

        # Check DSN format
        dsn_format_rule = next(r for r in sentry_rules if r["rule"] == "dsn_format")
        if not re.match(dsn_format_rule["pattern"], sentry_dsn):
            self.issues["errors"].append(dsn_format_rule["error_message"])
            return False

        return True

    def _validate_allowed_hosts(self) -> bool:
        """Validate ALLOWED_HOSTS configuration."""
        if (
            not self.rules.get("validation_rules", {})
            .get("security", {})
            .get("allowed_hosts", {})
            .get("enabled", True)
        ):
            return True

        host_rules = self.rules["validation_rules"]["security"]["allowed_hosts"]

        try:
            allowed_hosts = json.loads(os.getenv("ALLOWED_HOSTS", "[]"))
            env = os.getenv("ENVIRONMENT", "").lower()

            if env == "production":
                for rule in host_rules.get("production_rules", []):
                    if rule["rule"] == "no_wildcards" and "*" in allowed_hosts:
                        self.issues["security_concerns"].append(rule["error_message"])
                        return False

            return True
        except json.JSONDecodeError:
            self.issues["errors"].append("ALLOWED_HOSTS must be a valid JSON array")
            return False

    def _update_metrics(self):
        """Update validation metrics."""
        end_time = time.time()
        self.metrics.validation_time_ms = (end_time - self.start_time) * 1000
        self.metrics.error_count = len(self.issues["errors"])
        self.metrics.warning_count = len(self.issues["warnings"])
        self.metrics.security_count = len(self.issues["security_concerns"])
        self.metrics.errors = self.issues["errors"]
        self.metrics.warnings = self.issues["warnings"]
        self.metrics.security_concerns = self.issues["security_concerns"]
        self.metrics.last_validation = datetime.now(timezone.utc).isoformat()

        # Save metrics to file
        with open("validation_metrics.json", "w") as f:
            json.dump(self.metrics.model_dump(), f, indent=2)

    def print_report(self):
        """Print validation report."""
        print("\nTemplate Configuration Validation Report")
        print("=" * 40)

        if not any(self.issues.values()):
            print("✅ All validation checks passed!")
            return

        if self.issues["errors"]:
            print("\n❌ Errors:")
            for error in self.issues["errors"]:
                print(f"  - {error}")

        if self.issues["warnings"]:
            print("\n⚠️  Warnings:")
            for warning in self.issues["warnings"]:
                print(f"  - {warning}")

        if self.issues["security_concerns"]:
            print("\n⚠️  Security Concerns:")
            for concern in self.issues["security_concerns"]:
                print(f"  - {concern}")


def main():
    """Main entry point for configuration validation."""
    validator = TemplateConfigValidator()
    success = validator.validate_settings()
    validator.print_report()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
