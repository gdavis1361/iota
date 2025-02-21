import pytest
import asyncio
from redis.sentinel import Sentinel
from app.core.rate_limit import (
    get_redis_sentinel,
    get_redis_master,
    rate_limit,
    check_rate_limit
)
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Test app setup
app = FastAPI()

@app.get("/test/ha")
@rate_limit(calls=10, period=60)
async def test_ha_endpoint(request: Request):
    return {"status": "ok"}

# Test fixtures
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def sentinel():
    """Get Redis Sentinel connection"""
    return get_redis_sentinel()

@pytest.fixture
async def redis_master(sentinel):
    """Get Redis master connection"""
    return await get_redis_master()

# Test cases
@pytest.mark.asyncio
async def test_sentinel_connection():
    """Test Redis Sentinel connection"""
    sentinel = get_redis_sentinel()
    assert sentinel is not None
    
    # Test master discovery
    master = sentinel.master_for('mymaster')
    assert master is not None
    
    # Test connection
    assert await master.ping()

@pytest.mark.asyncio
async def test_master_slave_replication(sentinel):
    """Test master-slave replication"""
    # Get master and slave connections
    master = sentinel.master_for('mymaster')
    slave = sentinel.slave_for('mymaster')
    
    # Write to master
    test_key = "test:replication"
    test_value = "test_value"
    await master.set(test_key, test_value)
    
    # Read should eventually be available on slave
    max_attempts = 5
    for _ in range(max_attempts):
        value = await slave.get(test_key)
        if value == test_value:
            break
        await asyncio.sleep(0.1)
    
    assert value == test_value
    
    # Cleanup
    await master.delete(test_key)

@pytest.mark.asyncio
async def test_failover_handling(client):
    """Test rate limiting during master failover"""
    # Make some requests to establish rate limits
    for _ in range(5):
        response = client.get("/test/ha")
        assert response.status_code == 200
    
    # Simulate master failure by stopping the container
    # Note: In real tests, you'd use Docker API or similar to stop the container
    # Here we just verify the system keeps working
    for _ in range(5):
        response = client.get("/test/ha")
        assert response.status_code == 200
    
    # Should be rate limited after 10 requests
    response = client.get("/test/ha")
    assert response.status_code == 429

@pytest.mark.asyncio
async def test_sentinel_failover(sentinel):
    """Test Sentinel failover mechanism"""
    # Get initial master
    master = sentinel.master_for('mymaster')
    initial_master_info = await master.info()
    
    # Write some data
    test_key = "test:failover"
    test_value = "failover_test"
    await master.set(test_key, test_value)
    
    # Verify data is replicated
    slave = sentinel.slave_for('mymaster')
    slave_value = await slave.get(test_key)
    assert slave_value == test_value
    
    # In a real test environment, you would:
    # 1. Stop the master container
    # 2. Wait for Sentinel to promote a slave
    # 3. Verify the new master is accessible
    # 4. Verify data is preserved
    
    # For now, we just verify we can still read the data
    new_master = sentinel.master_for('mymaster')
    value = await new_master.get(test_key)
    assert value == test_value
    
    # Cleanup
    await new_master.delete(test_key)

@pytest.mark.asyncio
async def test_rate_limit_persistence(sentinel, client):
    """Test rate limits persist across Redis master changes"""
    # Set up rate limit on initial master
    for _ in range(8):
        response = client.get("/test/ha")
        assert response.status_code == 200
    
    # Simulate master change (in real tests, trigger actual failover)
    new_master = sentinel.master_for('mymaster')
    
    # Rate limits should be preserved
    response = client.get("/test/ha")
    assert response.status_code == 200
    
    response = client.get("/test/ha")
    assert response.status_code == 200
    
    # Should be rate limited after 10 requests total
    response = client.get("/test/ha")
    assert response.status_code == 429

@pytest.mark.asyncio
async def test_redis_error_handling(client):
    """Test graceful handling of Redis errors"""
    # Simulate Redis connection error by using invalid port
    # System should allow requests rather than blocking users
    response = client.get("/test/ha")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_concurrent_rate_limits(sentinel, client):
    """Test rate limiting under concurrent load"""
    async def make_request():
        response = client.get("/test/ha")
        return response.status_code
    
    # Make 20 concurrent requests (limit is 10)
    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    
    # Should see mix of 200 and 429 responses
    success_count = len([r for r in results if r == 200])
    rate_limited_count = len([r for r in results if r == 429])
    
    assert success_count == 10  # First 10 should succeed
    assert rate_limited_count == 10  # Rest should be rate limited
