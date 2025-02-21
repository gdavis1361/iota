"""Base configuration classes and environment settings."""
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import (
    AnyHttpUrl,
    PostgresDsn,
    RedisDsn,
    Field,
    field_validator,
    ConfigDict
)
from pydantic_settings import BaseSettings

from .rate_limit import RateLimitConfig, EndpointLimit

# Project base directory
BASE_DIR = Path(__file__).resolve().parents[3]

class EnvironmentType(str, Enum):
    """Valid environment types for the application."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def is_production(cls, env: str) -> bool:
        """Check if environment is production."""
        return env.lower() == cls.PRODUCTION.value

class Settings(BaseSettings):
    """
    Core application settings with comprehensive validation.
    
    This class centralizes all configuration management and provides:
    1. Environment variable loading
    2. Type validation
    3. Cross-field validation
    4. Default values
    """
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env"
    )
    
    # Basic settings
    APP_NAME: str = "iota"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ALLOWED_HOSTS: list = ["localhost", "127.0.0.1"]
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URI: Optional[RedisDsn] = None
    
    # Rate Limiting
    rate_limit_config: RateLimitConfig = Field(
        default_factory=lambda: RateLimitConfig(
            default_window=60,
            default_max_requests=100,
            endpoint_limits={},
            redis_host="localhost",
            redis_port=6379
        )
    )
    
    # Monitoring
    SENTRY_DSN: Optional[AnyHttpUrl] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    
    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_uri(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        """Construct database URI from components."""
        if isinstance(v, str):
            return v
            
        values = info.data
        return str(PostgresDsn.build(
            scheme="postgresql",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST", "localhost"),
            port=values.get("POSTGRES_PORT", 5432),
            path=f"/{values.get('POSTGRES_DB', '')}"
        ))
    
    @field_validator("REDIS_URI", mode="before")
    def assemble_redis_uri(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        """Construct Redis URI from components."""
        if isinstance(v, str):
            return v
            
        values = info.data
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get("REDIS_PASSWORD") else ""
        return f"redis://{password_part}{values.get('REDIS_HOST', 'localhost')}:{values.get('REDIS_PORT', 6379)}/0"
    
    @field_validator("ENVIRONMENT")
    def validate_environment(cls, v: str, info: Dict[str, Any]) -> str:
        """Ensure environment is valid and apply production safeguards."""
        if EnvironmentType.is_production(v):
            # Production environment requires strict settings
            values = info.data
            if not values.get("SECRET_KEY") or len(values.get("SECRET_KEY", "")) < 32:
                raise ValueError("Production environment requires a strong SECRET_KEY")
            if "*" in values.get("ALLOWED_HOSTS", []):
                raise ValueError("Production environment cannot have wildcard ALLOWED_HOSTS")
        return v

def create_settings() -> Settings:
    """Create settings instance with environment variables."""
    return Settings()

def create_test_settings() -> Settings:
    """Create settings instance with test-specific defaults.
    
    This provides a consistent test configuration that:
    1. Uses testing environment
    2. Sets secure defaults for required fields
    3. Uses in-memory/local services
    """
    from .rate_limit import EndpointLimit
    
    test_values = {
        "ENVIRONMENT": EnvironmentType.TESTING,
        "SECRET_KEY": "test_secret_key_thats_at_least_32_chars_long",
        "POSTGRES_PASSWORD": "test_db_password",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": 5432,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "DEBUG": True,
        "rate_limit_config": RateLimitConfig(
            default_window=60,
            default_max_requests=100,
            endpoint_limits={
                "/test/endpoint": EndpointLimit(
                    window=30,
                    max_requests=50
                )
            },
            redis_host="localhost",
            redis_port=6379
        )
    }
    return Settings(**test_values)
