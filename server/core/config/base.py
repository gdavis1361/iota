"""Base configuration classes and environment settings."""
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import (
    BaseModel,
    AnyHttpUrl,
    PostgresDsn,
    RedisDsn,
    Field,
    validator
)

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

class Settings(BaseModel):
    """
    Core application settings with comprehensive validation.
    
    This class centralizes all configuration management and provides:
    1. Environment variable loading
    2. Type validation
    3. Cross-field validation
    4. Default values
    """
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
    
    # Monitoring
    SENTRY_DSN: Optional[AnyHttpUrl] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_uri(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        """Construct database URI from components."""
        if isinstance(v, str):
            return v
            
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST", "localhost"),
            port=values.get("POSTGRES_PORT", 5432),
            path=f"/{values.get('POSTGRES_DB', '')}"
        )
    
    @validator("REDIS_URI", pre=True)
    def assemble_redis_uri(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        """Construct Redis URI from components."""
        if isinstance(v, str):
            return v
            
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get("REDIS_PASSWORD") else ""
        return f"redis://{password_part}{values.get('REDIS_HOST', 'localhost')}:{values.get('REDIS_PORT', 6379)}/0"
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        """Ensure environment is valid and apply production safeguards."""
        if EnvironmentType.is_production(v):
            # Production environment requires strict settings
            if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
                raise ValueError("Production environment requires a strong SECRET_KEY")
            if "*" in cls.ALLOWED_HOSTS:
                raise ValueError("Production environment cannot have wildcard ALLOWED_HOSTS")
        return v

# Global settings instance
settings = Settings()
