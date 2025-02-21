"""Tests for the rate limit cleanup script."""
import time
from unittest.mock import Mock, patch
import pytest
import redis

from scripts.cleanup_rate_limits import RateLimitCleaner

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch('redis.Redis') as mock:
        mock.return_value.scan_iter.return_value = []
        mock.return_value.zcount.return_value = 0
        mock.return_value.delete.return_value = True
        yield mock.return_value

@pytest.fixture
def cleaner(mock_redis):
    """Create a RateLimitCleaner instance with mocked Redis."""
    return RateLimitCleaner(
        redis_host="localhost",
        redis_port=6379,
        redis_password=None,
        redis_db=0
    )

def test_init_default_params():
    """Test initialization with default parameters."""
    cleaner = RateLimitCleaner()
    assert cleaner.dry_run is False
    assert cleaner.metrics_registry is not None

def test_init_custom_params():
    """Test initialization with custom parameters."""
    cleaner = RateLimitCleaner(
        redis_host="testhost",
        redis_port=6380,
        redis_password="secret",
        redis_db=1,
        dry_run=True
    )
    assert cleaner.dry_run is True

def test_cleanup_expired_windows_empty(cleaner, mock_redis):
    """Test cleanup with no windows."""
    mock_redis.scan_iter.return_value = []
    cleaned = cleaner.cleanup_expired_windows()
    assert cleaned == 0
    mock_redis.scan_iter.assert_called_once_with("rate_limit:*")

def test_cleanup_expired_windows_with_data(cleaner, mock_redis):
    """Test cleanup with expired windows."""
    mock_redis.scan_iter.return_value = [
        "rate_limit:test1",
        "rate_limit:test2"
    ]
    mock_redis.zcount.return_value = 0
    cleaned = cleaner.cleanup_expired_windows()
    assert cleaned == 2
    assert mock_redis.delete.call_count == 2

def test_cleanup_expired_windows_with_active(cleaner, mock_redis):
    """Test cleanup with active windows."""
    mock_redis.scan_iter.return_value = [
        "rate_limit:test1",
        "rate_limit:test2"
    ]
    mock_redis.zcount.return_value = 1
    cleaned = cleaner.cleanup_expired_windows()
    assert cleaned == 0
    assert mock_redis.delete.call_count == 0

def test_cleanup_expired_windows_dry_run(cleaner, mock_redis):
    """Test cleanup in dry run mode."""
    cleaner.dry_run = True
    mock_redis.scan_iter.return_value = ["rate_limit:test"]
    mock_redis.zcount.return_value = 0
    cleaned = cleaner.cleanup_expired_windows()
    assert cleaned == 1
    mock_redis.delete.assert_not_called()

def test_cleanup_expired_windows_redis_error(cleaner, mock_redis):
    """Test cleanup handling Redis errors."""
    mock_redis.scan_iter.side_effect = redis.RedisError("Test error")
    cleaned = cleaner.cleanup_expired_windows()
    assert cleaned == 0

def test_aggregate_metrics(cleaner, mock_redis):
    """Test metric aggregation."""
    mock_redis.scan_iter.return_value = [
        "rate_limit:login_attempts:127.0.0.1",
        "rate_limit:api:/test"
    ]
    mock_redis.zcount.return_value = 5
    cleaner.aggregate_metrics()
    assert mock_redis.zcount.call_count == 2

def test_compress_windows(cleaner, mock_redis):
    """Test window compression."""
    mock_redis.scan_iter.return_value = [
        "rate_limit:test1",
        "rate_limit:test2"
    ]
    cleaner.compress_windows()
    assert mock_redis.zremrangebyscore.call_count == 2

def test_run_maintenance(cleaner, mock_redis):
    """Test full maintenance run."""
    mock_redis.scan_iter.return_value = ["rate_limit:test"]
    mock_redis.zcount.return_value = 0
    cleaner.run_maintenance()
    mock_redis.scan_iter.assert_called()
    mock_redis.zcount.assert_called()

def test_run_maintenance_error(cleaner, mock_redis):
    """Test maintenance error handling."""
    mock_redis.scan_iter.side_effect = redis.RedisError("Test error")
    with pytest.raises(Exception):
        cleaner.run_maintenance()

@pytest.mark.parametrize("redis_error", [
    redis.ConnectionError,
    redis.TimeoutError,
    redis.AuthenticationError
])
def test_cleanup_specific_redis_errors(cleaner, mock_redis, redis_error):
    """Test handling of specific Redis errors."""
    mock_redis.scan_iter.side_effect = redis_error("Test error")
    cleaned = cleaner.cleanup_expired_windows()
    assert cleaned == 0

def test_metrics_registry_write(cleaner, mock_redis, tmp_path):
    """Test metrics writing."""
    metrics_file = tmp_path / "test_metrics.prom"
    with patch('prometheus_client.write_to_textfile') as mock_write:
        cleaner._write_aggregated_metrics({
            "violations_total": 10,
            "failed_logins_total": 5
        })
        mock_write.assert_called_once()
