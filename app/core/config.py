"""Configuration settings."""
import os
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", env_file_encoding="utf-8"
    )

    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    SERVER_HOST: str = "http://localhost:8000"
    SERVER_NAME: str = "IOTA Server"
    PROJECT_NAME: str = "IOTA"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_DB: str = "jsquared"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    DATABASE_URL: Optional[str] = None
    SQL_ECHO: bool = False
    DEBUG: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        """Assemble database connection URL."""
        if isinstance(v, str):
            return v

        # Get values from the model
        data = info.data
        if not all(
            key in data
            for key in ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SERVER", "POSTGRES_DB"]
        ):
            # If any required fields are missing, return None and let the model handle validation
            return None

        url = PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=data.get("POSTGRES_USER"),
            password=data.get("POSTGRES_PASSWORD"),
            host=data.get("POSTGRES_SERVER"),
            path=data.get("POSTGRES_DB"),
        )
        return str(url)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
