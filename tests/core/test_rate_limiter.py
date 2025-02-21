"""Tests for rate limiter implementation."""
import pytest
import time
from unittest.mock import Mock, patch
from redis.exceptions import RedisError

from server.app.core.rate_limiter import RateLimiter

@pytest.fixture
def rate_limit_config():
    """Create test rate limit configuration."""
    return RateLimitConfig(
        default_window=60,
        default_max_requests=100,
        endpoint_limits={
            "/test/endpoint": {"window": 30, "max_requests": 50}
        },
        redis_host="localhost",
        redis_port=6379
    )

@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = Mock()
    mock.ping.return_value = True
    return mock

@pytest.fixture
def rate_limiter(rate_limit_config, mock_redis):
    """Create rate limiter with mock Redis."""
    return RateLimiter(rate_limit_config, mock_redis)

def test_rate_limiter_initialization(test_settings, mock_redis):
    """Test rate limiter initialization."""
    limiter = RateLimiter(test_settings.rate_limit_config, mock_redis)
    assert limiter.config == test_settings.rate_limit_config
    mock_redis.ping.assert_called_once()

def test_rate_limiter_redis_failure(test_settings, mock_redis):
    """Test rate limiter handles Redis connection failure."""
    mock_redis.ping.side_effect = RedisError("Connection failed")
    with pytest.raises(RedisError):
        RateLimiter(test_settings.rate_limit_config, mock_redis)

def test_rate_limit_check_first_request(rate_limiter, mock_redis):
    """Test first request is always allowed."""
    mock_redis.get.return_value = None
    mock_redis.ttl.return_value = -2
    
    allowed, wait_time, headers = rate_limiter.check_rate_limit("127.0.0.1")
    
    assert allowed is True
    assert wait_time == 0
    assert headers["X-RateLimit-Remaining"] == "99"
    mock_redis.setex.assert_called_once()

def test_rate_limit_check_endpoint_specific(rate_limiter, mock_redis):
    """Test endpoint-specific rate limits."""
    mock_redis.get.return_value = "1"
    mock_redis.ttl.return_value = 30
    
    allowed, wait_time, headers = rate_limiter.check_rate_limit(
        "127.0.0.1",
        endpoint="/test/endpoint"
    )
    
    assert allowed is True
    assert wait_time == 0
    assert headers["X-RateLimit-Limit"] == "50"
    assert headers["X-RateLimit-Remaining"] == "48"

def test_rate_limit_exceeded(rate_limiter, mock_redis):
    """Test rate limit exceeded response."""
    mock_redis.get.return_value = "101"  # Over limit
    mock_redis.ttl.return_value = 30
    
    allowed, wait_time, headers = rate_limiter.check_rate_limit("127.0.0.1")
    
    assert allowed is False
    assert wait_time == 30
    assert "Retry-After" in headers
    assert headers["X-RateLimit-Remaining"] == "0"

def test_rate_limit_redis_error(rate_limiter, mock_redis):
    """Test rate limiter handles Redis errors gracefully."""
    mock_redis.get.side_effect = RedisError("Operation failed")
    
    allowed, wait_time, headers = rate_limiter.check_rate_limit("127.0.0.1")
    
    # Should fail open
    assert allowed is True
    assert wait_time == 0
    assert headers == {}
