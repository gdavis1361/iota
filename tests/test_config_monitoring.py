import unittest
from typing import Any, Dict

from server.core.config_schema import ConfigurationMetrics, ConfigurationSchema, ConfigVersion


class TestConfigMonitoring(unittest.TestCase):
    """Test suite for configuration monitoring functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.metrics = ConfigurationMetrics.get_instance()
        self.config = ConfigurationSchema(version=ConfigVersion.V2_0.value)

    def test_metrics_structure(self) -> None:
        """Test that the metrics have the expected structure."""
        self.assertIsInstance(self.metrics.dict(), dict)
        self.assertEqual(self.metrics.error_count, 0)
        self.assertEqual(self.metrics.warning_count, 0)
        self.assertEqual(self.metrics.validation_count, 0)

    def test_metrics_recording(self) -> None:
        """Test that metrics recording works."""
        self.metrics.record_validation(100.0)
        self.assertEqual(self.metrics.validation_count, 1)
        self.assertEqual(self.metrics.validation_time_ms, 100.0)
        self.assertIsNotNone(self.metrics.last_validation_timestamp)

    def test_error_recording(self) -> None:
        """Test error recording functionality."""
        self.metrics.record_error("test_field", "test error")
        self.assertEqual(self.metrics.error_count, 1)
        self.assertIn("test_field", self.metrics.validation_errors)
        self.assertEqual(self.metrics.validation_errors["test_field"], "test error")


if __name__ == "__main__":
    unittest.main()
