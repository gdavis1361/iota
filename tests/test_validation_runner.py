"""Test suite for configuration validation test runner."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.run_validation_test import run_validation


class TestValidationRunner(unittest.TestCase):
    """Test cases for validation test runner."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_env = {
            "ENVIRONMENT": "testing",
            "SECRET_KEY": "this_is_a_very_secure_secret_key_for_testing_32",
            "DEBUG": "false",
            "ALLOWED_HOSTS": '["localhost", "127.0.0.1"]',
            "SENTRY_ENABLED": "false",
        }

    def test_successful_validation(self):
        """Test successful validation run."""
        with patch("subprocess.run") as mock_run:
            # Mock successful validation
            mock_run.return_value = MagicMock(
                stdout="✅ All validation checks passed!", stderr="", returncode=0
            )

            result = run_validation(self.test_env)
            self.assertTrue(result)

            # Verify subprocess call
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            self.assertEqual(args[0], ["python", "scripts/validate_config.py"])
            self.assertEqual(kwargs["env"].get("ENVIRONMENT"), "testing")

    def test_failed_validation(self):
        """Test failed validation run."""
        with patch("subprocess.run") as mock_run:
            # Mock validation failure
            mock_run.return_value = MagicMock(
                stdout="❌ Validation failed", stderr="Error: Invalid configuration", returncode=1
            )

            bad_env = self.test_env.copy()
            bad_env["SECRET_KEY"] = "short"  # Invalid secret key

            result = run_validation(bad_env)
            self.assertFalse(result)

    def test_environment_override(self):
        """Test environment variable override."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Override existing environment variable
            with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                run_validation(self.test_env)

                args, kwargs = mock_run.call_args
                self.assertEqual(
                    kwargs["env"].get("ENVIRONMENT"),
                    "testing",  # Should use test_env value
                    "Environment override failed",
                )

    def test_subprocess_error(self):
        """Test handling of subprocess errors."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.SubprocessError("Command failed")

            with self.assertRaises(RuntimeError):
                run_validation(self.test_env)


if __name__ == "__main__":
    unittest.main()
