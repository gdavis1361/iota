"""Performance tests for rate limiter implementation."""
import time
import pytest
from redis import Redis
from concurrent.futures import ThreadPoolExecutor

from server.core.config import create_test_settings
from server.app.core.rate_limiter import RateLimiter

@pytest.fixture
def test_settings():
    return create_test_settings()

@pytest.fixture
def redis_client():
    client = Redis(host='localhost', port=6379, db=0)
    yield client
    client.flushdb()  # Clean up after tests

@pytest.fixture
def rate_limiter(test_settings, redis_client):
    return RateLimiter(test_settings.rate_limit_config, redis_client)

def test_rate_limiter_single_thread_performance(rate_limiter, benchmark):
    """Test rate limiter performance in single thread."""
    def check_limit():
        return rate_limiter.check_rate_limit("test-user")
    
    # Benchmark should show < 1ms per operation
    result = benchmark(check_limit)
    assert result.stats.mean < 0.001

def test_rate_limiter_concurrent_performance(rate_limiter):
    """Test rate limiter performance with concurrent requests."""
    NUM_REQUESTS = 1000
    MAX_WORKERS = 10
    
    def check_limit():
        return rate_limiter.check_rate_limit("test-user-concurrent")
    
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(lambda _: check_limit(), range(NUM_REQUESTS)))
    end = time.perf_counter()
    
    total_time = end - start
    ops_per_second = NUM_REQUESTS / total_time
    
    # Should handle at least 1000 ops/second
    assert ops_per_second >= 1000
    
    # Verify rate limiting worked
    assert sum(1 for r in results if r[0]) < NUM_REQUESTS

def test_redis_operation_performance(redis_client, benchmark):
    """Test basic Redis operation performance."""
    def redis_ops():
        redis_client.set("test-key", "test-value")
        redis_client.get("test-key")
        redis_client.delete("test-key")
    
    # Benchmark should show < 3ms for set+get+delete
    result = benchmark(redis_ops)
    assert result.stats.mean < 0.003

def test_rate_limiter_memory_usage(rate_limiter, redis_client):
    """Test memory usage patterns of rate limiter."""
    # Get initial memory
    initial_memory = redis_client.info()['used_memory']
    
    # Create many rate limit entries
    NUM_KEYS = 10000
    for i in range(NUM_KEYS):
        rate_limiter.check_rate_limit(f"test-user-{i}")
    
    # Get final memory
    final_memory = redis_client.info()['used_memory']
    memory_per_key = (final_memory - initial_memory) / NUM_KEYS
    
    # Should use less than 100 bytes per key on average
    assert memory_per_key < 100

def test_configuration_load_performance(benchmark):
    """Test configuration loading performance."""
    def load_config():
        return create_test_settings()
    
    # Benchmark should show < 5ms for config creation
    result = benchmark(load_config)
    assert result.stats.mean < 0.005
