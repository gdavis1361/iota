"""Configuration schema versioning and validation."""

import time
from enum import Enum
from typing import ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ConfigVersion(str, Enum):
    """Configuration schema versions."""

    V1_0 = "1.0"  # Initial version
    V1_1 = "1.1"  # Added Sentry configuration
    V2_0 = "2.0"  # Migrated to Pydantic v2


class ConfigurationSchema(BaseModel):
    """Base configuration schema with version tracking."""

    model_config = ConfigDict(extra="allow")

    version: str = Field(
        default=ConfigVersion.V2_0.value, description="Configuration schema version"
    )

    @classmethod
    def get_schema_changes(cls) -> Dict[str, str]:
        """Get description of changes between versions."""
        return {
            "1.0": "Initial version with core settings",
            "1.1": "Added Sentry configuration and monitoring",
            "2.0": "Migrated to Pydantic v2, enhanced validation",
        }

    @classmethod
    def get_migration_notes(cls, from_version: str, to_version: str) -> str:
        """Get migration notes between versions."""
        migrations = {
            (
                "1.0",
                "1.1",
            ): """
                Changes:
                - Added SENTRY_* configuration options
                - Added performance monitoring settings

                Required Actions:
                1. Add SENTRY_ENABLED setting
                2. If Sentry is enabled, provide SENTRY_DSN
                """,
            (
                "1.1",
                "2.0",
            ): """
                Changes:
                - Updated to Pydantic v2 syntax
                - Enhanced validation rules
                - Added JSON format requirement for lists

                Required Actions:
                1. Update ALLOWED_HOSTS to use JSON format
                2. Review all validation rules
                3. Test configuration in all environments
                """,
        }
        return migrations.get((from_version, to_version), "No migration notes available")


class ConfigurationMetrics(BaseModel):
    """Configuration system metrics."""

    _instance: ClassVar[Optional["ConfigurationMetrics"]] = None

    # Timing metrics
    validation_time_ms: float = Field(default=0.0)
    last_validation_timestamp: Optional[float] = None
    validation_count: int = Field(default=0)

    # Error metrics
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    validation_errors: Dict[str, str] = Field(default_factory=dict)

    # Performance metrics
    last_reload_timestamp: Optional[float] = None
    average_validation_time_ms: float = Field(default=0.0)
    peak_validation_time_ms: float = Field(default=0.0)

    @classmethod
    def get_instance(cls) -> "ConfigurationMetrics":
        """Get or create the singleton metrics instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_validation(self, duration_ms: float) -> None:
        """Record a validation event with timing information."""
        self.validation_time_ms = duration_ms
        self.last_validation_timestamp = time.time()
        self.validation_count += 1

        # Update performance metrics
        if duration_ms > self.peak_validation_time_ms:
            self.peak_validation_time_ms = duration_ms

        # Update running average
        if self.validation_count == 1:
            self.average_validation_time_ms = duration_ms
        else:
            self.average_validation_time_ms = (
                self.average_validation_time_ms * (self.validation_count - 1) + duration_ms
            ) / self.validation_count

    def record_error(self, field: str, message: str) -> None:
        """Record a validation error."""
        self.error_count += 1
        self.validation_errors[field] = message

    def record_warning(self) -> None:
        """Record a validation warning."""
        self.warning_count += 1

    def reset(self) -> None:
        """Reset all metrics."""
        self.validation_time_ms = 0.0
        self.last_validation_timestamp = None
        self.validation_count = 0
        self.error_count = 0
        self.warning_count = 0
        self.validation_errors.clear()
        self.last_reload_timestamp = None
        self.average_validation_time_ms = 0.0
        self.peak_validation_time_ms = 0.0


class ValidationSeverity(str, Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationRule(BaseModel):
    """Base validation rule schema."""

    severity: ValidationSeverity = Field(
        default=ValidationSeverity.ERROR, description="Severity level for validation failures"
    )


class ResourceSpecification(BaseModel):
    """Resource specification schema."""

    model_config = ConfigDict(extra="allow")

    pattern: str = Field(description="Regex pattern to match the resource specification")
    severity: ValidationSeverity = Field(
        default=ValidationSeverity.WARNING,
        description="Severity level for missing resource specifications",
    )


class ValidationRequirements(BaseModel):
    """Base requirements schema with required and recommended fields."""

    required: Dict[str, ValidationSeverity] = Field(
        default_factory=dict, description="Required fields and their severity levels"
    )
    recommended: Dict[str, Union[ValidationSeverity, Dict[str, ValidationSeverity]]] = Field(
        default_factory=dict, description="Recommended fields and their severity levels"
    )


class CloudRequirements(BaseModel):
    """Cloud service requirements schema."""

    required: Dict[str, Dict[str, ValidationSeverity]] = Field(
        default_factory=dict, description="Required cloud services, operations, and monitoring"
    )
    recommended: Dict[str, Dict[str, ValidationSeverity]] = Field(
        default_factory=dict, description="Recommended cloud services, operations, and monitoring"
    )


class InfrastructureRequirements(ValidationRequirements):
    """Infrastructure-specific requirements schema."""

    resource_specifications: Dict[str, ResourceSpecification] = Field(
        default_factory=dict, description="Resource specifications and their validation patterns"
    )


class TemplateValidationSchema(BaseModel):
    """Schema for template validation rules."""

    model_config = ConfigDict(extra="allow")

    metadata_fields: ValidationRequirements = Field(
        default_factory=ValidationRequirements, description="Metadata field validation requirements"
    )
    security_requirements: ValidationRequirements = Field(
        default_factory=ValidationRequirements, description="Security validation requirements"
    )
    cloud_requirements: CloudRequirements = Field(
        default_factory=CloudRequirements, description="Cloud service validation requirements"
    )
    cost_requirements: ValidationRequirements = Field(
        default_factory=ValidationRequirements, description="Cost documentation requirements"
    )
    infrastructure_requirements: ValidationRequirements = Field(
        default_factory=ValidationRequirements,
        description="Infrastructure documentation requirements",
    )


class SchemaVersion(BaseModel):
    major: int = Field(ge=0, description="Major version for breaking changes")
    minor: int = Field(ge=0, description="Minor version for backward-compatible feature additions")
    patch: int = Field(ge=0, description="Patch version for backward-compatible bug fixes")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_str(cls, version_str: str) -> "SchemaVersion":
        try:
            major, minor, patch = map(int, version_str.split("."))
            return cls(major=major, minor=minor, patch=patch)
        except ValueError:
            raise ValueError(f"Invalid version string: {version_str}. Expected format: X.Y.Z")

    def is_compatible_with(self, other: "SchemaVersion") -> bool:
        """Check if this version is backward compatible with another version"""
        return self.major == other.major and (
            self.minor > other.minor or (self.minor == other.minor and self.patch >= other.patch)
        )


class ValidationRulesSchema(BaseModel):
    """Top-level schema for validation rules configuration."""

    model_config = ConfigDict(extra="allow")

    version: SchemaVersion = Field(
        default=SchemaVersion(major=1, minor=0, patch=0),
        description="Schema version following semantic versioning",
    )
    template_types: Dict[str, TemplateValidationSchema] = Field(
        default_factory=dict, description="Validation rules for each template type"
    )

    def validate_config_file(self) -> List[str]:
        """Validate the entire configuration file and return any errors."""
        errors = []

        # Validate template types exist
        if not self.template_types:
            errors.append("No template types defined in configuration")

        # Validate each template type has required sections
        for template_type, schema in self.template_types.items():
            if not schema.metadata_fields.required:
                errors.append(f"Template type '{template_type}' missing required metadata fields")
            if not schema.security_requirements.required:
                errors.append(
                    f"Template type '{template_type}' missing required security requirements"
                )
            if not schema.cloud_requirements.required:
                errors.append(f"Template type '{template_type}' missing required cloud services")

        return errors
