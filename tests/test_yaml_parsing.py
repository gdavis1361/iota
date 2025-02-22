"""Test suite for YAML validation rules parsing."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.validate_config import TemplateConfigValidator


class TestYAMLRuleParsing(unittest.TestCase):
    """Test cases for YAML validation rules parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_rules = {
            "validation_rules": {
                "environment": {
                    "enabled": True,
                    "allowed_values": ["development", "testing", "staging", "production"],
                    "error_message": "Invalid ENVIRONMENT value: {value}",
                },
                "security": {
                    "secret_key": {
                        "enabled": True,
                        "min_length": 32,
                        "error_message": "SECRET_KEY is too short",
                    }
                },
            }
        }

        # Create test rules file
        self.test_rules_path = Path("config/test_validation_rules.yaml")
        os.makedirs(self.test_rules_path.parent, exist_ok=True)
        with open(self.test_rules_path, "w") as f:
            yaml.dump(self.test_rules, f)

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_rules_path.exists():
            self.test_rules_path.unlink()

    def test_load_validation_rules(self):
        """Test loading validation rules from YAML."""
        validator = TemplateConfigValidator()
        rules = validator.rules

        self.assertIsInstance(rules, dict)
        self.assertIn("validation_rules", rules)
        self.assertIn("environment", rules["validation_rules"])
        self.assertIn("security", rules["validation_rules"])

    def test_environment_validation(self):
        """Test environment validation rules."""
        validator = TemplateConfigValidator()

        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            self.assertTrue(validator._validate_environment())

        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            self.assertFalse(validator._validate_environment())

    def test_security_validation(self):
        """Test security validation rules."""
        validator = TemplateConfigValidator()

        with patch.dict(os.environ, {"SECRET_KEY": "x" * 32}):
            self.assertTrue(validator._validate_security_settings())

        with patch.dict(os.environ, {"SECRET_KEY": "short"}):
            self.assertFalse(validator._validate_security_settings())

    def test_metrics_collection(self):
        """Test validation metrics collection."""
        validator = TemplateConfigValidator()

        # Trigger some validation failures
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid", "SECRET_KEY": "short"}):
            validator.validate_settings()

        self.assertGreater(validator.metrics.error_count, 0)
        self.assertGreater(validator.metrics.validation_time_ms, 0)


if __name__ == "__main__":
    unittest.main()
