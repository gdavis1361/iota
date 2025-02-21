import pytest
from pydantic import ValidationError
from app.core.config import Settings, EnvironmentType

def test_minimal_env_validation():
    """Test that minimal required environment variables are validated."""
    env_vars = {
        "SECRET_KEY": "test_secret_key",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "ENVIRONMENT": "testing"
    }
    settings = Settings(**env_vars)
    assert settings.SECRET_KEY.get_secret_value() == "test_secret_key"
    assert str(settings.DATABASE_URL) == env_vars["DATABASE_URL"]
    assert settings.ENVIRONMENT == EnvironmentType.TESTING

def test_production_env_validation():
    """Test that production environment requires stricter validation."""
    env_vars = {
        "SECRET_KEY": "short",  # Too short for production
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "ENVIRONMENT": "production"
    }
    with pytest.raises(AssertionError):
        settings = Settings(**env_vars)
        settings.validate_production_settings()

def test_redis_url_validation():
    """Test Redis URL validation."""
    env_vars = {
        "SECRET_KEY": "test_secret_key",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "ENVIRONMENT": "testing",
        "REDIS_URL": "invalid-url"
    }
    with pytest.raises(ValidationError):
        Settings(**env_vars)

def test_cors_origins_validation():
    """Test CORS origins validation."""
    env_vars = {
        "SECRET_KEY": "test_secret_key",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "ENVIRONMENT": "testing",
        "BACKEND_CORS_ORIGINS": "http://localhost:3000,http://localhost:3001"
    }
    settings = Settings(**env_vars)
    assert len(settings.BACKEND_CORS_ORIGINS) == 2
    assert all(str(origin).startswith("http") for origin in settings.BACKEND_CORS_ORIGINS)
