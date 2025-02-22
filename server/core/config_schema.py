"""Configuration schema versioning and validation."""

import time
from enum import Enum
from typing import Any, ClassVar, Dict, Optional

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
