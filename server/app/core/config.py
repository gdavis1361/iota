from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project base directory
BASE_DIR = Path(__file__).resolve().parents[3]


class EnvironmentType(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings with comprehensive validation and documentation."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==== Core API Configuration ====
    PROJECT_NAME: str = "IOTA"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="Current environment type",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode. Should be False in production.",
    )

    # ==== Security & Authentication ====
    SECRET_KEY: SecretStr = Field(
        ...,  # Required field
        description="Secret key for JWT token generation and other cryptographic operations",
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used for JWT token generation",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=5,  # Must be at least 5 minutes
        description="Access token expiration time in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,  # Must be at least 1 day
        description="Refresh token expiration time in days",
    )

    # ==== Database Configuration ====
    POSTGRES_SERVER: str = Field(
        default="localhost",
        description="PostgreSQL server hostname",
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        description="PostgreSQL server port",
    )
    POSTGRES_USER: str = Field(
        default="postgres",
        description="PostgreSQL username",
    )
    POSTGRES_PASSWORD: str = Field(
        default="postgres",
        description="PostgreSQL password",
    )
    POSTGRES_DB: str = Field(
        default="iota",
        description="PostgreSQL database name",
    )
    DATABASE_URL: Optional[PostgresDsn] = Field(
        default=None,
        description="PostgreSQL connection string",
    )
    SQL_ECHO: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        """Assemble database URL from components."""
        if isinstance(v, str):
            return v

        values = info.data
        db_name = values.get("POSTGRES_DB", "")

        # Handle test database - don't append _test if it's already there
        if values.get("ENVIRONMENT") == EnvironmentType.TESTING and not db_name.endswith("_test"):
            db_name = f"{db_name}_test"

        return PostgresDsn.build(
            scheme="postgresql",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=db_name,
        )

    # ==== Redis Configuration ====
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=10,
        ge=1,
        description="Maximum number of Redis connections",
    )

    # ==== Rate Limiting ====
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        ge=1,
        description="Number of requests allowed per window",
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=60,
        ge=1,
        description="Time window for rate limiting in seconds",
    )

    # ==== CORS & Security ====
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=[],
        description="List of allowed CORS origins",
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="List of allowed hosts",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Assemble CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """Assemble allowed hosts from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    def validate_production_settings(self) -> None:
        """Validate that production environment has secure settings."""
        if self.ENVIRONMENT == EnvironmentType.PRODUCTION:
            assert not self.DEBUG, "Debug mode must be disabled in production"
            assert self.SECRET_KEY, "Secret key must be set in production"
            assert self.ALLOWED_HOSTS, "Allowed hosts must be set in production"


@lru_cache()
def get_settings() -> Settings:
    """Get settings instance with caching."""
    return Settings()


settings = get_settings()
