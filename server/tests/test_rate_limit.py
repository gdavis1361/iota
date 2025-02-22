from unittest.mock import AsyncMock, patch

import pytest
from app.core.rate_limit import rate_limit
from app.main import app
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch("app.core.redis.init_redis_pool") as mock:
        redis_mock = AsyncMock()
        mock.return_value = redis_mock
        yield redis_mock


@pytest.mark.asyncio
async def test_auth_rate_limit_under_limit(client: AsyncClient, mock_redis):
    """Test rate limit under the limit"""
    # Setup mock Redis responses
    mock_redis.get.return_value = "2"  # 2 previous requests
    mock_redis.pipeline.return_value.execute.return_value = [3]  # Incremented to 3

    response = await client.post(
        "/api/v1/auth/token", data={"username": "test@example.com", "password": "testpass"}
    )
    assert response.status_code != 429  # Not rate limited


@pytest.mark.asyncio
async def test_auth_rate_limit_exceeded(client: AsyncClient, mock_redis):
    """Test rate limit exceeded"""
    # Setup mock Redis responses
    mock_redis.get.return_value = "100"  # Over the limit
    mock_redis.pipeline.return_value.execute.return_value = [101]

    response = await client.post(
        "/api/v1/auth/token", data={"username": "test@example.com", "password": "testpass"}
    )
    assert response.status_code == 429
    assert "Too many requests" in response.text


@pytest.mark.asyncio
async def test_api_rate_limit_under_limit(client: AsyncClient, mock_redis):
    """Test API rate limit under the limit"""
    # Setup mock Redis responses
    mock_redis.get.return_value = "5"  # Under the limit
    mock_redis.pipeline.return_value.execute.return_value = [6]

    response = await client.get("/api/v1/users/me")
    assert response.status_code != 429  # Not rate limited


@pytest.mark.asyncio
async def test_api_rate_limit_exceeded(client: AsyncClient, mock_redis):
    """Test API rate limit exceeded"""
    # Setup mock Redis responses
    mock_redis.get.return_value = "100"  # Over the limit
    mock_redis.pipeline.return_value.execute.return_value = [101]

    response = await client.get("/api/v1/users/me")
    assert response.status_code == 429
    assert "Too many requests" in response.text


@pytest.mark.asyncio
async def test_rate_limit_counter_expiry(client: AsyncClient, mock_redis):
    """Test rate limit counter expiry"""
    # Setup mock Redis responses
    mock_redis.get.return_value = None  # No previous requests
    mock_redis.pipeline.return_value.execute.return_value = [1]  # First request

    response = await client.post(
        "/api/v1/auth/token", data={"username": "test@example.com", "password": "testpass"}
    )
    assert response.status_code != 429  # Not rate limited


@pytest.mark.asyncio
async def test_rate_limit_headers(client: AsyncClient, mock_redis):
    """Test that rate limit headers are set correctly"""
    # Setup mock Redis responses
    mock_redis.get.return_value = "2"  # 2 previous requests
    mock_redis.pipeline.return_value.execute.return_value = [3]  # Incremented to 3

    response = await client.post(
        "/api/v1/auth/token", data={"username": "test@example.com", "password": "testpass"}
    )
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_different_endpoints_separate_limits(client: AsyncClient, mock_redis):
    """Test that different endpoints have separate rate limits"""

    # Setup different mock values for different endpoints
    def get_side_effect(key):
        if "auth_token" in key:
            return "2"
        elif "users_me" in key:
            return "30"
        return None

    mock_redis.get.side_effect = get_side_effect

    # Test auth endpoint
    auth_response = await client.post(
        "/api/v1/auth/token", data={"username": "test@example.com", "password": "testpass"}
    )
    assert auth_response.status_code != 429  # Not rate limited

    # Test users/me endpoint
    users_response = await client.get("/api/v1/users/me")
    assert users_response.status_code != 429  # Not rate limited
