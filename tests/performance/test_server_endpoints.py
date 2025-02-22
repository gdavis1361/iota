#!/usr/bin/env python3
"""Unit tests for the test server endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from test_server import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("test_server.redis_client") as mock:
        yield mock


def test_health_check_success(client, mock_redis):
    """Test health check endpoint with Redis connected."""
    mock_redis.ping.return_value = True
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "redis": "connected"}


def test_health_check_redis_failure(client, mock_redis):
    """Test health check endpoint with Redis disconnected."""
    mock_redis.ping.side_effect = Exception("Redis connection failed")
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "redis": "disconnected"}


def test_get_data(client):
    """Test data retrieval endpoint."""
    response = client.get("/api/v1/data")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "timestamp" in data


def test_create_data(client):
    """Test data creation endpoint."""
    response = client.post("/api/v1/data/create")
    assert response.status_code == 201
    assert response.json() == {"message": "Data created successfully"}


def test_get_metrics(client, mock_redis):
    """Test metrics retrieval endpoint."""
    mock_redis.get.side_effect = ["100", "5"]
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == "100"
    assert data["rate_limited_requests"] == "5"


def test_get_metrics_redis_error(client, mock_redis):
    """Test metrics retrieval with Redis errors."""
    mock_redis.get.side_effect = Exception("Redis error")
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 0
    assert data["rate_limited_requests"] == 0


def test_get_users(client):
    """Test user data retrieval endpoint."""
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 100
    assert data["active_users"] == 50


def test_get_token(client):
    """Test token retrieval endpoint."""
    response = client.get("/api/v1/auth/token")
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["expires_in"] == 3600


def test_create_token(client):
    """Test token creation endpoint."""
    response = client.post("/api/v1/auth/token")
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["expires_in"] == 3600


if __name__ == "__main__":
    pytest.main(["-v", __file__])
