"""Redis test configuration."""

import os

import pytest
import redis
from redis.sentinel import Sentinel


@pytest.fixture(scope="session")
def redis_config():
    """Redis configuration for tests"""
    return {
        "master_host": "localhost",
        "master_port": int(os.getenv("REDIS_MASTER_PORT", 6381)),
        "sentinel_host": "localhost",
        "sentinel_port": int(os.getenv("REDIS_SENTINEL_PORT", 26380)),
        "master_name": os.getenv("REDIS_MASTER_NAME", "mymaster"),
    }


@pytest.fixture(scope="session")
def redis_master(redis_config):
    """Direct connection to Redis master"""
    client = redis.Redis(
        host=redis_config["master_host"],
        port=redis_config["master_port"],
        decode_responses=True,
    )
    try:
        client.ping()
        yield client
    finally:
        client.close()


@pytest.fixture(scope="session")
def redis_sentinel(redis_config):
    """Redis Sentinel connection"""
    sentinel = Sentinel(
        [(redis_config["sentinel_host"], redis_config["sentinel_port"])],
        decode_responses=True,
    )
    yield sentinel
