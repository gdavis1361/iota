"""Configuration validation and metrics tracking."""
import time
from typing import Dict, Any, Optional, ClassVar
from pydantic import BaseModel, Field

class ConfigurationSchema(BaseModel):
    """Configuration schema with version tracking."""
    version: str = Field(
        default="1.0",
        description="Configuration schema version"
    )
    
    @classmethod
    def get_schema_changes(cls) -> Dict[str, str]:
        """Get description of changes between versions."""
        return {
            "1.0": "Initial version with core settings",
            "1.1": "Added Sentry configuration and monitoring",
            "2.0": "Future: Migration to Pydantic v2"
        }

class ConfigurationMetrics(BaseModel):
    """
    Configuration system metrics tracking.
    
    This class provides:
    1. Validation timing metrics
    2. Error tracking
    3. Performance monitoring
    """
    _instance: ClassVar[Optional['ConfigurationMetrics']] = None
    
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
    def get_instance(cls) -> 'ConfigurationMetrics':
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
                (self.average_validation_time_ms * (self.validation_count - 1) + duration_ms) 
                / self.validation_count
            )
    
    def record_error(self, error_msg: str, field: str) -> None:
        """Record a validation error."""
        self.error_count += 1
        self.validation_errors[field] = error_msg
    
    def record_warning(self, warning_msg: str) -> None:
        """Record a validation warning."""
        self.warning_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of configuration metrics."""
        return {
            "validation_count": self.validation_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "average_validation_time_ms": self.average_validation_time_ms,
            "peak_validation_time_ms": self.peak_validation_time_ms,
            "last_validation": self.last_validation_timestamp,
            "last_reload": self.last_reload_timestamp
        }
