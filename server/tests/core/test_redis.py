import pytest
from app.core.config import settings
from app.core.redis import close_redis_client, get_redis_client, init_redis_pool, redis_client
from redis.asyncio import Redis


@pytest.mark.asyncio
async def test_init_redis_pool():
    """Test Redis pool initialization"""
    # Initial state should be None
    global redis_client
    redis_client = None

    # Initialize pool and get client
    client = await init_redis_pool()
    assert isinstance(client, Redis)
    assert client.connection_pool is not None

    # Test connection works
    assert await client.ping()

    # Test pool reuse
    client2 = await init_redis_pool()
    assert client2.connection_pool is client.connection_pool  # Same pool is reused

    # Cleanup
    await close_redis_client()


@pytest.mark.asyncio
async def test_get_redis_client():
    """Test getting Redis client"""
    # Should raise error if not initialized
    with pytest.raises(RuntimeError):
        get_redis_client()

    # Initialize pool first
    client = await init_redis_pool()

    # Get client
    same_client = get_redis_client()
    assert same_client is client

    # Test connection works
    await client.set("test_key", "test_value")
    value = await client.get("test_key")
    assert value == "test_value"  # decode_responses=True

    # Cleanup
    await client.delete("test_key")
    await close_redis_client()


@pytest.mark.asyncio
async def test_close_redis_client():
    """Test closing Redis client"""
    # Initialize pool
    client = await init_redis_pool()
    assert client is not None
    assert client.connection_pool is not None

    # Close everything
    await close_redis_client()

    # Check globals are None
    assert redis_client is None

    # Trying to get client should raise error
    with pytest.raises(RuntimeError):
        get_redis_client()
