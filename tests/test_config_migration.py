import unittest
from pathlib import Path
from typing import Any, Dict

from server.core.config_schema import ConfigurationSchema, ConfigVersion


class TestConfigMigration(unittest.TestCase):
    """Test suite for configuration migration functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = ConfigurationSchema(version=ConfigVersion.V2_0.value)
        self.test_data_dir = Path(__file__).parent / "data"

    def test_version_tracking(self) -> None:
        """Test that version tracking is properly maintained."""
        self.assertEqual(self.config.version, ConfigVersion.V2_0.value)
        self.assertIsInstance(self.config.version, str)
        # Version should be in format x.y
        parts = self.config.version.split(".")
        self.assertEqual(len(parts), 2)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_schema_changes(self) -> None:
        """Test that schema changes are properly documented."""
        changes = ConfigurationSchema.get_schema_changes()
        self.assertIsInstance(changes, dict)
        self.assertIn("1.0", changes)
        self.assertIn("1.1", changes)
        self.assertIn("2.0", changes)

    def test_migration_notes(self) -> None:
        """Test that migration notes are available."""
        notes = ConfigurationSchema.get_migration_notes("1.0", "1.1")
        self.assertIsInstance(notes, str)
        self.assertNotEqual(notes, "No migration notes available")

        notes = ConfigurationSchema.get_migration_notes("1.1", "2.0")
        self.assertIsInstance(notes, str)
        self.assertNotEqual(notes, "No migration notes available")

    def test_backwards_compatibility(self) -> None:
        """Test backwards compatibility of config migrations."""
        # Create configs for different versions
        v1_config = ConfigurationSchema(version=ConfigVersion.V1_0.value)
        v2_config = ConfigurationSchema(version=ConfigVersion.V2_0.value)

        # Basic version checks
        self.assertEqual(v1_config.version, ConfigVersion.V1_0.value)
        self.assertEqual(v2_config.version, ConfigVersion.V2_0.value)

        # Check schema changes
        changes = ConfigurationSchema.get_schema_changes()
        self.assertIn(v1_config.version, changes)
        self.assertIn(v2_config.version, changes)


if __name__ == "__main__":
    unittest.main()
