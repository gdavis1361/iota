#!/usr/bin/env python3
"""Unit tests for the test environment setup components."""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from setup_test_env import (
    check_app_server,
    check_redis_connection,
    load_test_data,
    setup_environment,
)

import redis


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("redis.Redis") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_requests():
    """Mock requests for testing."""
    with patch("requests.get") as mock:
        yield mock


@pytest.fixture
def test_config():
    """Sample test configuration."""
    return {
        "endpoints": {"/api/v1/test": {"method": "GET", "weight": 50, "expected_status": 200}},
        "redis_monitoring": {
            "metrics": ["used_memory", "connected_clients"],
            "thresholds": {"max_memory_usage": "1GB", "max_clients": 1000},
        },
    }


def test_check_redis_connection_success(mock_redis):
    """Test successful Redis connection."""
    mock_redis.ping.return_value = True
    mock_redis.info.return_value = {"redis_version": "7.2.7"}

    success, message = check_redis_connection()
    assert success
    assert "Redis v7.2.7" in message
    mock_redis.ping.assert_called_once()


def test_check_redis_connection_failure(mock_redis):
    """Test Redis connection failure."""
    mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")

    success, message = check_redis_connection()
    assert not success
    assert "Connection refused" in message


def test_check_app_server_success(mock_requests):
    """Test successful app server check."""
    mock_requests.return_value.status_code = 200

    success, message = check_app_server()
    assert success
    assert "running" in message
    mock_requests.assert_called_once()


def test_check_app_server_failure(mock_requests):
    """Test app server check failure."""
    mock_requests.side_effect = requests.ConnectionError()

    success, message = check_app_server()
    assert not success
    assert "not running" in message


def test_load_test_data_success(mock_redis, test_config, tmp_path):
    """Test successful test data loading."""
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(test_config))

    success, message = load_test_data(mock_redis, str(config_file))
    assert success
    assert "successfully" in message
    mock_redis.hset.assert_called_once()


def test_load_test_data_invalid_config(mock_redis, tmp_path):
    """Test loading test data with invalid config."""
    config_file = tmp_path / "invalid_config.json"
    config_file.write_text("invalid json")

    success, message = load_test_data(mock_redis, str(config_file))
    assert not success
    assert "Failed" in message


@patch("setup_test_env.check_redis_connection")
@patch("setup_test_env.check_app_server")
@patch("setup_test_env.load_test_data")
def test_setup_environment_success(mock_load, mock_app, mock_redis, test_config, tmp_path):
    """Test successful environment setup."""
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(test_config))

    mock_redis.return_value = (True, "Redis running")
    mock_app.return_value = (True, "App running")
    mock_load.return_value = (True, "Data loaded")

    status = setup_environment(str(config_file))

    assert status["redis"]["running"]
    assert status["app_server"]["running"]
    assert status["test_data"]["loaded"]


@patch("setup_test_env.check_redis_connection")
@patch("setup_test_env.check_app_server")
def test_setup_environment_partial_failure(mock_app, mock_redis, test_config, tmp_path):
    """Test environment setup with partial failures."""
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(test_config))

    mock_redis.return_value = (False, "Redis failed")
    mock_app.return_value = (True, "App running")

    status = setup_environment(str(config_file))

    assert not status["redis"]["running"]
    assert status["app_server"]["running"]
    assert not status["test_data"]["loaded"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
