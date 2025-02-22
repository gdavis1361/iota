"""Tests for schema version compatibility."""

import pytest

from server.core.config_schema import SchemaVersion, ValidationRulesSchema


def test_schema_version_parsing():
    """Test parsing version strings."""
    version = SchemaVersion.from_str("1.2.3")
    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3

    with pytest.raises(ValueError):
        SchemaVersion.from_str("invalid")

    with pytest.raises(ValueError):
        SchemaVersion.from_str("1.2")

    with pytest.raises(ValueError):
        SchemaVersion.from_str("1.2.3.4")


def test_schema_version_compatibility():
    """Test version compatibility checks."""
    v1_0_0 = SchemaVersion(major=1, minor=0, patch=0)
    v1_1_0 = SchemaVersion(major=1, minor=1, patch=0)
    v1_1_1 = SchemaVersion(major=1, minor=1, patch=1)
    v2_0_0 = SchemaVersion(major=2, minor=0, patch=0)

    # Same major version, higher minor is compatible
    assert v1_1_0.is_compatible_with(v1_0_0)

    # Same major.minor version, higher patch is compatible
    assert v1_1_1.is_compatible_with(v1_1_0)

    # Different major versions are not compatible
    assert not v2_0_0.is_compatible_with(v1_0_0)
    assert not v1_0_0.is_compatible_with(v2_0_0)


def test_schema_version_string_representation():
    """Test version string formatting."""
    version = SchemaVersion(major=1, minor=2, patch=3)
    assert str(version) == "1.2.3"


def test_schema_version_validation():
    """Test version field validation in schema."""
    # Default version
    schema = ValidationRulesSchema(template_types={})
    assert schema.version == SchemaVersion(major=1, minor=0, patch=0)

    # Custom version
    schema = ValidationRulesSchema(
        version=SchemaVersion(major=2, minor=1, patch=0), template_types={}
    )
    assert str(schema.version) == "2.1.0"

    # Invalid version values
    with pytest.raises(ValueError):
        ValidationRulesSchema(version=SchemaVersion(major=-1, minor=0, patch=0))

    with pytest.raises(ValueError):
        ValidationRulesSchema(version=SchemaVersion(major=1, minor=-1, patch=0))

    with pytest.raises(ValueError):
        ValidationRulesSchema(version=SchemaVersion(major=1, minor=0, patch=-1))
