"""Base configuration for the application."""

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Base settings for the application."""

    # Application settings
    APP_NAME: str = "IOTA"
    DEBUG: bool = False

    # Security settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database settings
    DATABASE_URL: str

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Rate limiting settings
    RATE_LIMIT_PER_MINUTE: int = 60


def create_settings() -> Settings:
    """Create settings instance with environment variables."""
    return Settings()


def create_test_settings() -> Settings:
    """
    Create settings instance with test-specific defaults.

    This provides a consistent test configuration that:
    1. Uses testing environment
    2. Sets secure defaults for required fields
    3. Uses in-memory/local services
    """
    return Settings(
        DEBUG=True,
        SECRET_KEY="test-secret-key-must-be-at-least-32-chars-long",
        DATABASE_URL="sqlite:///:memory:",
        LOG_LEVEL="DEBUG",
    )
