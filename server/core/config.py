"""Application configuration management."""
import json
import re
import logging
from functools import lru_cache
from typing import Dict, List, Optional, Union, Any
from pydantic import field_validator, BaseModel, SecretStr, Field, AnyHttpUrl, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings."""
    
    # Core settings
    APP_NAME: str = Field("iota", description="Application name")
    APP_VERSION: str = Field("1.0.0", description="Application version")
    DEBUG: bool = Field(False, description="Debug mode")
    ENVIRONMENT: str = Field("development", description="Environment (development, staging, production)")
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FORMAT: str = Field("json", description="Log format (json or console)")
    CORRELATION_ID_HEADER: str = Field("X-Correlation-ID", description="Header for correlation ID")
    SECRET_KEY: SecretStr = Field(..., description="Secret key for security")  # Required field
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed hosts")
    
    # Sentry settings
    SENTRY_ENABLED: bool = Field(False, description="Enable/disable Sentry integration")
    SENTRY_DSN: Optional[str] = Field(None, description="Sentry DSN")
    SENTRY_ENVIRONMENT: str = Field("development", description="Override environment for Sentry")
    SENTRY_RELEASE: Optional[str] = Field(None, description="Release version for Sentry")
    SENTRY_SERVER_NAME: Optional[str] = Field(None, description="Server name for Sentry")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(0.1, description="Sentry traces sample rate (0.0 to 1.0)")
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(0.1, description="Sentry profiles sample rate (0.0 to 1.0)")
    SENTRY_MAX_BREADCRUMBS: int = Field(100, description="Maximum number of breadcrumbs")
    SENTRY_DEBUG: bool = Field(False, description="Enable Sentry debug mode")
    SENTRY_METADATA: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata to include in Sentry events")
    
    # Performance monitoring settings
    SLOW_REQUEST_THRESHOLD_MS: float = Field(1000.0, description="Threshold for slow requests in milliseconds")
    ERROR_RATE_THRESHOLD: float = Field(0.1, description="Error rate threshold for increasing sampling")
    SLOW_RATE_THRESHOLD: float = Field(0.1, description="Slow request rate threshold for increasing sampling")
    SAMPLING_WINDOW_SECONDS: int = Field(60, description="Window size for sampling calculations")
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str, info: ValidationInfo) -> str:
        """Validate environment setting."""
        valid_environments = {"development", "staging", "production", "test"}
        if v.lower() not in valid_environments:
            error_msg = f"Invalid environment '{v}'. Must be one of: {', '.join(valid_environments)}"
            logger.error("Configuration validation error", extra={
                "field": "ENVIRONMENT",
                "value": v,
                "error": error_msg,
                "valid_options": list(valid_environments)
            })
            raise ValueError(error_msg)
        logger.info("Environment validated", extra={"environment": v})
        return v.lower()

    @field_validator("SENTRY_DSN")
    @classmethod
    def validate_sentry_dsn(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate Sentry DSN format when Sentry is enabled."""
        if not info.data.get("SENTRY_ENABLED", False):
            return v
            
        if not v:
            error_msg = "SENTRY_DSN is required when Sentry is enabled"
            logger.error("Configuration validation error", extra={
                "field": "SENTRY_DSN",
                "error": error_msg
            })
            raise ValueError(error_msg)
            
        dsn_pattern = r'^https://[^:]+@[^/]+/\d+$'
        if not re.match(dsn_pattern, v):
            error_msg = "Invalid Sentry DSN format"
            logger.error("Configuration validation error", extra={
                "field": "SENTRY_DSN",
                "error": error_msg,
                "pattern": dsn_pattern
            })
            raise ValueError(error_msg)
        logger.info("Sentry DSN validated")
        return v

    @field_validator("ALLOWED_HOSTS")
    @classmethod
    def validate_allowed_hosts(cls, v: List[str], info: ValidationInfo) -> List[str]:
        """Validate allowed hosts is not empty."""
        if not v:
            error_msg = "ALLOWED_HOSTS cannot be empty"
            logger.error("Configuration validation error", extra={
                "field": "ALLOWED_HOSTS",
                "error": error_msg
            })
            raise ValueError(error_msg)
        logger.info("Allowed hosts validated", extra={"hosts": v})
        return v

    @field_validator("SENTRY_METADATA")
    @classmethod
    def validate_sentry_metadata(cls, v: Dict[str, Any], info: ValidationInfo) -> Dict[str, Any]:
        """Validate Sentry metadata."""
        try:
            # Test JSON serialization
            json.dumps(v)
            logger.info("Sentry metadata validated", extra={"keys": list(v.keys())})
            return v
        except Exception as e:
            error_msg = f"Invalid Sentry metadata: {str(e)}"
            logger.error("Configuration validation error", extra={
                "field": "SENTRY_METADATA",
                "error": error_msg
            })
            raise ValueError(error_msg)

    @field_validator("SENTRY_TRACES_SAMPLE_RATE", "SENTRY_PROFILES_SAMPLE_RATE",
                    "ERROR_RATE_THRESHOLD", "SLOW_RATE_THRESHOLD")
    @classmethod
    def validate_rate_values(cls, v: float, info: ValidationInfo) -> float:
        """Validate rate values are between 0 and 1."""
        if not 0 <= v <= 1:
            error_msg = f"Rate value must be between 0 and 1"
            logger.error("Configuration validation error", extra={
                "field": info.field_name,
                "value": v,
                "error": error_msg
            })
            raise ValueError(error_msg)
        logger.info(f"Rate value validated", extra={
            "field": info.field_name,
            "value": v
        })
        return v

    @field_validator("SLOW_REQUEST_THRESHOLD_MS", "SAMPLING_WINDOW_SECONDS")
    @classmethod
    def validate_positive_values(cls, v: Union[float, int], info: ValidationInfo) -> Union[float, int]:
        """Validate values are positive."""
        if v <= 0:
            error_msg = f"Value must be positive"
            logger.error("Configuration validation error", extra={
                "field": info.field_name,
                "value": v,
                "error": error_msg
            })
            raise ValueError(error_msg)
        logger.info(f"Positive value validated", extra={
            "field": info.field_name,
            "value": v
        })
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        # If we're in test environment, use test.env
        if kwargs.get("ENVIRONMENT") == "test" or "test" in kwargs.get("ENV_FILE", ""):
            kwargs.setdefault("APP_NAME", "test-app")
            kwargs.setdefault("DEBUG", True)
            kwargs.setdefault("SENTRY_ENABLED", False)  # Changed to False for tests
            kwargs.setdefault("SENTRY_ENVIRONMENT", "test")
            kwargs.setdefault("SENTRY_DEBUG", True)
            kwargs.setdefault("SENTRY_TRACES_SAMPLE_RATE", 1.0)
            kwargs.setdefault("SENTRY_PROFILES_SAMPLE_RATE", 1.0)
            kwargs.setdefault("SENTRY_METADATA", {"test_key": "test_value"})
        
        super().__init__(**kwargs)

# Initialize settings
_settings = None

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = initialize_settings()
    return _settings

def initialize_settings() -> Settings:
    """Initialize settings singleton."""
    global _settings
    
    logger.info("Initializing application settings")
    try:
        if _settings is not None:
            logger.info("Returning existing settings instance")
            return _settings
            
        settings = Settings()
        
        # Log successful initialization with key settings (excluding sensitive data)
        log_data = {
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "sentry_enabled": settings.SENTRY_ENABLED,
            "allowed_hosts": settings.ALLOWED_HOSTS
        }
        logger.info("Settings initialized successfully", extra=log_data)
        
        _settings = settings
        return settings
    except Exception as e:
        logger.critical("Failed to initialize settings", extra={
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise
