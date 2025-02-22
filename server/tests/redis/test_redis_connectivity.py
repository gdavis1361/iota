"""Redis Connectivity Tests.

This module contains tests for basic Redis connectivity, including master-replica
relationships and sentinel monitoring.
"""

import pytest
from redis.sentinel import Sentinel

import redis


@pytest.mark.redis
@pytest.mark.redis_sentinel
class TestRedisConnectivity:
    """Test suite for Redis connectivity."""

    def test_master_connection(self, redis_sentinel: Sentinel):
        """Verify basic connectivity with Redis master."""
        # Get master connection
        master = redis_sentinel.master_for("mymaster")

        # Test write operation
        assert master.set("test_key", "test_value")

        # Test read operation
        assert master.get("test_key") == "test_value"

        # Clean up
        master.delete("test_key")

    def test_replica_connection(self, redis_sentinel: Sentinel):
        """Verify replica connectivity and read-only mode."""
        # Get replica connection
        replica = redis_sentinel.slave_for("mymaster")

        # Write to master first
        master = redis_sentinel.master_for("mymaster")
        master.set("replica_test_key", "replica_test_value")

        # Verify replica can read
        assert replica.get("replica_test_key") == "replica_test_value"

        # Verify replica is read-only
        with pytest.raises(redis.ReadOnlyError):
            replica.set("new_key", "new_value")

        # Clean up
        master.delete("replica_test_key")

    def test_sentinel_monitoring(self, redis_sentinel: Sentinel):
        """Verify sentinel can see master and replicas."""
        # Get sentinel connection
        sentinel = redis_sentinel.sentinel_connection

        # Check master state
        master_state = sentinel.master("mymaster")
        assert master_state["role"] == "master"

        # Check replica count
        replicas = sentinel.slaves("mymaster")
        assert len(replicas) >= 1
        assert replicas[0]["role"] == "slave"
