"""
Unit tests for the configuration module.
"""
import os
import json
import pytest
from pathlib import Path
from pydantic import ValidationError
from pydantic_settings.sources import SettingsError
from server.core.config import Settings, get_settings, initialize_settings

@pytest.fixture
def test_env_path():
    return Path(__file__).parent / "test.env"

@pytest.fixture
def base_test_settings():
    # Store original env vars
    original_env = dict(os.environ)
    
    # Set base test env vars
    base_test_env_vars = {
        "ENV_FILE": str(test_env_path),
        "ENVIRONMENT": "test",
        "APP_NAME": "test-app",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "SECRET_KEY": "test-secret-key",
        "ALLOWED_HOSTS": '["test.com"]',
        "SENTRY_ENABLED": "true",
        "SENTRY_DSN": "https://test@test.ingest.sentry.io/test",
        "SENTRY_ENVIRONMENT": "test",
        "SENTRY_DEBUG": "true",
        "SENTRY_TRACES_SAMPLE_RATE": "1.0",
        "SENTRY_PROFILES_SAMPLE_RATE": "1.0",
        "SENTRY_METADATA": '{"test_key": "test_value"}'
    }
    
    os.environ.update(base_test_env_vars)
    
    yield
    
    # Restore original env vars
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def test_settings(base_test_settings, test_env_path):
    """Create test settings with specific overrides."""
    # Store original env vars
    original_env = dict(os.environ)
    
    # Set test-specific overrides
    test_env_vars = {
        "APP_NAME": "test-app",
        "APP_VERSION": "1.0.0",
        "DEBUG": "true",
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "json",
        "SECRET_KEY": "test-secret-key",
        "ALLOWED_HOSTS": '["test.com"]',
        "SENTRY_ENABLED": "true",
        "SENTRY_DSN": "https://test@test.ingest.sentry.io/1234",
        "SENTRY_ENVIRONMENT": "test",
        "SENTRY_DEBUG": "true",
        "SENTRY_TRACES_SAMPLE_RATE": "1.0",
        "SENTRY_PROFILES_SAMPLE_RATE": "1.0",
        "SENTRY_METADATA": '{"test_key": "test_value"}',
        "SLOW_REQUEST_THRESHOLD_MS": "1000.0",
        "ERROR_RATE_THRESHOLD": "0.1",
        "SLOW_RATE_THRESHOLD": "0.1",
        "SAMPLING_WINDOW_SECONDS": "60"
    }
    
    os.environ.update(test_env_vars)
    
    # Create new settings instance with overrides
    settings = Settings()
    
    yield settings
    
    # Restore original env vars
    os.environ.clear()
    os.environ.update(original_env)

def test_settings_singleton():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2

def test_settings_values(test_settings):
    """Test that settings are loaded correctly from test.env."""
    assert test_settings.APP_NAME == "test-app"
    assert test_settings.DEBUG is True
    assert test_settings.ENVIRONMENT == "test"
    assert test_settings.LOG_LEVEL == "DEBUG"

def test_sentry_settings(test_settings):
    """Test Sentry-specific settings."""
    assert test_settings.SENTRY_ENABLED is True
    assert test_settings.SENTRY_DSN == "https://test@test.ingest.sentry.io/1234"
    assert test_settings.SENTRY_ENVIRONMENT == "test"
    assert test_settings.SENTRY_DEBUG is True
    assert test_settings.SENTRY_TRACES_SAMPLE_RATE == 1.0
    assert test_settings.SENTRY_PROFILES_SAMPLE_RATE == 1.0

def test_sentry_metadata_parsing(test_settings):
    """Test parsing of SENTRY_METADATA JSON."""
    assert test_settings.SENTRY_METADATA == {"test_key": "test_value"}

def test_invalid_sentry_metadata(monkeypatch):
    """Test handling of invalid SENTRY_METADATA JSON."""
    monkeypatch.setenv("SENTRY_METADATA", "invalid json")
    with pytest.raises(SettingsError) as exc_info:
        Settings()
    assert "SENTRY_METADATA" in str(exc_info.value)

def test_settings_default_values():
    """Test default values when env vars are not set."""
    # Clear environment variables to test defaults
    env_backup = dict(os.environ)
    os.environ.clear()
    
    # Set required fields
    os.environ.update({
        "ENVIRONMENT": "development",
        "SECRET_KEY": "test-secret-key"
    })
    
    try:
        settings = Settings()
        
        # Test default values
        assert settings.APP_NAME == "iota"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"
        assert settings.CORRELATION_ID_HEADER == "X-Correlation-ID"
        assert settings.ALLOWED_HOSTS == ["*"]
        assert settings.SENTRY_ENABLED is False
        assert settings.SENTRY_DSN is None
        assert settings.SENTRY_ENVIRONMENT == "development"
        assert settings.SENTRY_METADATA == {}
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(env_backup)

def test_secret_key_required():
    """Test that SECRET_KEY is required."""
    env_backup = dict(os.environ)
    os.environ.clear()
    
    # Set only environment
    os.environ["ENVIRONMENT"] = "development"
    
    try:
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "SECRET_KEY" in str(exc_info.value)
    finally:
        os.environ.clear()
        os.environ.update(env_backup)

def test_missing_mandatory_env_vars():
    """Test behavior when mandatory environment variables are missing."""
    env_backup = dict(os.environ)
    os.environ.clear()
    
    try:
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        error_str = str(exc_info.value)
        assert "SECRET_KEY" in error_str
    finally:
        os.environ.clear()
        os.environ.update(env_backup)

def test_performance_monitoring_settings(test_settings):
    """Test performance monitoring settings."""
    assert test_settings.SLOW_REQUEST_THRESHOLD_MS == 1000.0
    assert test_settings.ERROR_RATE_THRESHOLD == 0.1
    assert test_settings.SLOW_RATE_THRESHOLD == 0.1
    assert test_settings.SAMPLING_WINDOW_SECONDS == 60

def test_invalid_sampling_rates():
    """Test validation of sampling rates."""
    invalid_values = {
        "SENTRY_TRACES_SAMPLE_RATE": "2.0",  # > 1.0
        "SENTRY_PROFILES_SAMPLE_RATE": "-0.1",  # < 0.0
    }
    
    for key, value in invalid_values.items():
        os.environ[key] = value
        with pytest.raises(ValidationError):
            Settings()

def test_initialize_settings():
    """Test settings initialization function."""
    # First call should create settings
    settings1 = initialize_settings()
    assert settings1 is not None
    
    # Second call should return same instance
    settings2 = initialize_settings()
    assert settings2 is settings1

def test_invalid_environment_value(monkeypatch):
    """Test behavior with invalid environment value."""
    monkeypatch.setenv("ENVIRONMENT", "invalid_env")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "ENVIRONMENT" in str(exc_info.value)

def test_complex_sentry_metadata(monkeypatch):
    """Test handling of complex nested SENTRY_METADATA JSON."""
    complex_metadata = {
        "app_info": {
            "version": "1.0.0",
            "environment": "test"
        },
        "tags": ["test", "validation"],
        "nested": {
            "level1": {
                "level2": "value"
            }
        }
    }
    monkeypatch.setenv("SENTRY_METADATA", json.dumps(complex_metadata))
    settings = Settings()
    assert settings.SENTRY_METADATA == complex_metadata

def test_invalid_sampling_rate_combinations(monkeypatch):
    """Test invalid combinations of sampling rates."""
    test_cases = [
        {"SENTRY_TRACES_SAMPLE_RATE": "1.5", "SENTRY_PROFILES_SAMPLE_RATE": "0.5"},
        {"SENTRY_TRACES_SAMPLE_RATE": "0.5", "SENTRY_PROFILES_SAMPLE_RATE": "-0.1"},
        {"SENTRY_TRACES_SAMPLE_RATE": "-1", "SENTRY_PROFILES_SAMPLE_RATE": "2.0"},
    ]
    
    for case in test_cases:
        for key, value in case.items():
            monkeypatch.setenv(key, value)
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "must be between 0 and 1" in str(exc_info.value)

def test_empty_allowed_hosts(monkeypatch):
    """Test behavior with empty ALLOWED_HOSTS."""
    monkeypatch.setenv("ALLOWED_HOSTS", "[]")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "ALLOWED_HOSTS" in str(exc_info.value)

def test_malformed_sentry_dsn(monkeypatch):
    """Test various malformed Sentry DSN values."""
    invalid_dsns = [
        "not-a-url",
        "http:/missing-host",
        "https://:password@host.com/1",
        "https://project@/1",
    ]
    
    for dsn in invalid_dsns:
        monkeypatch.setenv("SENTRY_ENABLED", "true")
        monkeypatch.setenv("SENTRY_DSN", dsn)
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "SENTRY_DSN" in str(exc_info.value)

def test_performance_threshold_validation(monkeypatch):
    """Test validation of performance monitoring thresholds."""
    invalid_thresholds = [
        {"SLOW_REQUEST_THRESHOLD_MS": "-1.0"},
        {"ERROR_RATE_THRESHOLD": "1.5"},
        {"SLOW_RATE_THRESHOLD": "-0.1"},
        {"SAMPLING_WINDOW_SECONDS": "0"},
    ]
    
    for thresholds in invalid_thresholds:
        for key, value in thresholds.items():
            monkeypatch.setenv(key, value)
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert any(key in str(exc_info.value) for key in thresholds.keys())
