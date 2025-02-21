"""Test configuration and fixtures for failover tests."""

import pytest


@pytest.fixture
async def redis_sentinel():
    """Create a Redis Sentinel connection."""
    from redis.sentinel import Sentinel

    sentinel = Sentinel(
        [("localhost", 26379), ("localhost", 26380), ("localhost", 26381)]
    )
    yield sentinel
