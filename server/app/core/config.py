from typing import List, Optional, Union, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic import (
    AnyHttpUrl,
    EmailStr,
    Field,
    PostgresDsn,
    field_validator,
    validator,
    SecretStr,
    RedisDsn,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project base directory
BASE_DIR = Path(__file__).resolve().parents[3]

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    """
    Application settings with comprehensive validation and documentation.
    Variables are grouped by their functional category for clarity.
    """
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

    # ==== Core API Configuration ====
    PROJECT_NAME: str = "JSquared"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="Current environment type"
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode. Should be False in production."
    )

    # ==== Security & Authentication ====
    SECRET_KEY: SecretStr = Field(
        ...,  # Required field
        description="Secret key for JWT token generation and other cryptographic operations"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used for JWT token generation"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=5,  # Must be at least 5 minutes
        description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,  # Must be at least 1 day
        description="Refresh token expiration time in days"
    )

    # ==== Database Configuration ====
    POSTGRES_SERVER: str = Field(
        default="localhost",
        description="PostgreSQL server hostname"
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        description="PostgreSQL server port"
    )
    POSTGRES_USER: str = Field(
        default="postgres",
        description="PostgreSQL username"
    )
    POSTGRES_PASSWORD: str = Field(
        default="postgres",
        description="PostgreSQL password"
    )
    POSTGRES_DB: str = Field(
        default="jsquared",
        description="PostgreSQL database name"
    )
    DATABASE_URL: Optional[PostgresDsn] = Field(
        default=None,
        description="PostgreSQL connection string"
    )
    SQL_ECHO: bool = Field(
        default=False,
        description="Enable SQL query logging"
    )

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_url(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"{values.get('POSTGRES_DB') or ''}"
        )

    # ==== Redis Configuration ====
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=10,
        ge=1,
        description="Maximum number of Redis connections"
    )

    # ==== Rate Limiting ====
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        ge=1,
        description="Number of requests allowed per window"
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=60,
        ge=1,
        description="Time window for rate limiting in seconds"
    )

    # ==== CORS & Security Headers ====
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=[],
        description="List of allowed CORS origins"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="List of allowed hosts"
    )

    # ==== AWS Configuration ====
    AWS_ACCESS_KEY_ID: Optional[str] = Field(
        default=None,
        description="AWS access key ID for S3 storage"
    )
    AWS_SECRET_ACCESS_KEY: Optional[SecretStr] = Field(
        default=None,
        description="AWS secret access key for S3 storage"
    )
    AWS_BUCKET_NAME: Optional[str] = Field(
        default=None,
        description="AWS S3 bucket name"
    )
    AWS_REGION: str = Field(
        default="us-east-1",
        description="AWS region for S3 bucket"
    )

    # ==== Logging Configuration ====
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )

    # ==== Email Configuration ====
    SMTP_TLS: bool = Field(
        default=True,
        description="Enable TLS for SMTP"
    )
    SMTP_HOST: Optional[str] = Field(
        default=None,
        description="SMTP server host"
    )
    SMTP_PORT: Optional[int] = Field(
        default=587,
        description="SMTP server port"
    )
    SMTP_USER: Optional[EmailStr] = Field(
        default=None,
        description="SMTP username"
    )
    SMTP_PASSWORD: Optional[SecretStr] = Field(
        default=None,
        description="SMTP password"
    )
    EMAILS_FROM_EMAIL: Optional[EmailStr] = Field(
        default=None,
        description="Email sender address"
    )
    EMAILS_FROM_NAME: Optional[str] = Field(
        default=None,
        description="Email sender name"
    )

    # ==== Validators ====
    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("ALLOWED_HOSTS")
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return upper_v

    def validate_production_settings(self) -> None:
        """Validate that production environment has secure settings."""
        if self.ENVIRONMENT == EnvironmentType.PRODUCTION:
            assert not self.DEBUG, "DEBUG must be False in production"
            assert len(str(self.SECRET_KEY)) >= 32, "SECRET_KEY too short"
            assert self.ALLOWED_HOSTS, "ALLOWED_HOSTS must be set in production"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get SQLAlchemy database URI"""
        return str(self.DATABASE_URL)

settings = Settings()
