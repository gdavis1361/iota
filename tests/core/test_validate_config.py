"""Tests for the configuration validation CLI tool."""
import os
import json
import pytest
from unittest.mock import patch
from pathlib import Path
from server.core.validate_config import load_env_file, validate_configuration

@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary environment file."""
    env_file = tmp_path / ".env.test"
    env_content = """APP_NAME=test-app
SECRET_KEY=x123456789012345678901234567890123
ENVIRONMENT=test
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_HOSTS=["localhost"]
SENTRY_ENABLED=false"""
    env_file.write_text(env_content)
    return env_file

@pytest.fixture
def mock_env():
    """Set up and tear down environment variables."""
    orig_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(orig_env)

def test_load_env_file_success(temp_env_file, mock_env):
    """Test successful environment file loading."""
    env_vars = load_env_file(str(temp_env_file))
    assert "APP_NAME" in env_vars
    assert env_vars["APP_NAME"] == "test-app"
    assert "SECRET_KEY" in env_vars
    assert len(env_vars["SECRET_KEY"]) >= 32

def test_load_env_file_not_found():
    """Test handling of missing environment file."""
    with pytest.raises(SystemExit) as exc_info:
        load_env_file("/nonexistent/file")
    assert exc_info.value.code == 1

def test_validate_configuration_success(mock_env):
    """Test successful configuration validation."""
    os.environ.update({
        "APP_NAME": "test-app",
        "SECRET_KEY": "x" * 32,
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "ALLOWED_HOSTS": '["localhost"]',
        "SENTRY_ENABLED": "false"
    })
    
    # Should not raise any exceptions
    validate_configuration(dict(os.environ))

def test_validate_configuration_invalid(mock_env):
    """Test configuration validation with invalid values."""
    os.environ.update({
        "APP_NAME": "test-app",
        "SECRET_KEY": "short",  # Invalid: too short
        "ENVIRONMENT": "invalid",  # Invalid: not in allowed list
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "ALLOWED_HOSTS": '["localhost"]',
        "SENTRY_ENABLED": "false"
    })
    
    with pytest.raises(SystemExit) as exc_info:
        validate_configuration(dict(os.environ))
    assert exc_info.value.code == 1

def test_validate_configuration_sentry_enabled(mock_env):
    """Test configuration validation with Sentry enabled."""
    os.environ.update({
        "APP_NAME": "test-app",
        "SECRET_KEY": "x" * 32,
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "ALLOWED_HOSTS": '["localhost"]',
        "SENTRY_ENABLED": "true",
        "SENTRY_DSN": "https://test@test.ingest.sentry.io/1234",
        "SENTRY_ENVIRONMENT": "test",
        "SENTRY_DEBUG": "false",
        "SENTRY_TRACES_SAMPLE_RATE": "0.1",
        "SENTRY_PROFILES_SAMPLE_RATE": "0.1"
    })
    
    # Should not raise any exceptions
    validate_configuration(dict(os.environ))

def test_validate_configuration_invalid_json(mock_env):
    """Test configuration validation with invalid JSON values."""
    os.environ.update({
        "APP_NAME": "test-app",
        "SECRET_KEY": "x" * 32,
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "ALLOWED_HOSTS": 'invalid-json',  # Invalid JSON
        "SENTRY_ENABLED": "false"
    })
    
    with pytest.raises(SystemExit) as exc_info:
        validate_configuration(dict(os.environ))
    assert exc_info.value.code == 1

@patch('logging.Logger.info')
def test_validate_configuration_logging(mock_info, mock_env):
    """Test that configuration validation logs expected information."""
    os.environ.update({
        "APP_NAME": "test-app",
        "SECRET_KEY": "x" * 32,
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "ALLOWED_HOSTS": '["localhost"]',
        "SENTRY_ENABLED": "false"
    })
    
    validate_configuration(dict(os.environ))
    
    # Verify expected log messages
    assert any("Configuration validation successful" in str(args) 
              for args in mock_info.call_args_list)
    assert any("Current configuration" in str(args) 
              for args in mock_info.call_args_list)
