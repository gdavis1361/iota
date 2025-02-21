"""Redis Failover Tests.

This module contains tests for Redis failover scenarios, including master failure
and recovery processes.
"""

import time
from typing import Generator

import docker
import pytest
import redis
from redis.sentinel import MasterNotFoundError, Sentinel


@pytest.fixture(scope="module")
def docker_client() -> Generator[docker.DockerClient, None, None]:
    """Create a Docker client for container management during tests."""
    client = docker.from_env()
    yield client
    client.close()


@pytest.mark.redis
@pytest.mark.redis_sentinel
class TestRedisFailover:
    """Test suite for Redis failover scenarios."""

    @pytest.fixture(scope="class")
    def docker_client(self):
        return docker.from_env()

    @pytest.mark.timeout(30)
    def test_master_failure_scenario(
        self, redis_sentinel: Sentinel, redis_config, docker_client: docker.DockerClient
    ):
        """Test failover when master fails"""
        # Get initial master
        initial_master = redis_sentinel.discover_master(redis_config["master_name"])
        assert initial_master is not None

        # Stop the master container
        master_container = docker_client.containers.get("redis-redis-master-1")
        master_container.stop()

        try:
            # Wait for failover (max 30 seconds)
            start_time = time.time()
            new_master = None
            while time.time() - start_time < 30:
                try:
                    new_master = redis_sentinel.discover_master(
                        redis_config["master_name"]
                    )
                    if new_master != initial_master:
                        break
                except MasterNotFoundError:
                    time.sleep(1)
                    continue

            assert new_master is not None
            assert new_master != initial_master

            # Verify we can still write to the new master
            master = redis_sentinel.master_for(
                redis_config["master_name"], decode_responses=True
            )
            assert master.set("failover_test", "success")
            assert master.get("failover_test") == "success"

        finally:
            # Cleanup: restart the original master
            master_container.start()

    @pytest.mark.timeout(30)
    def test_failover_speed(
        self, redis_sentinel: Sentinel, docker_client: docker.DockerClient
    ):
        """Measure failover timing."""
        start_time = time.time()

        try:
            # Stop master container
            master_container = docker_client.containers.get("redis-master")
            master_container.stop()

            # Wait for new master to be elected
            new_master = None
            timeout = 30  # timeout after 30 seconds
            while time.time() - start_time < timeout:
                try:
                    new_master = redis_sentinel.discover_master("mymaster")
                    break
                except redis.sentinel.MasterNotFoundError:
                    time.sleep(0.1)

            failover_time = time.time() - start_time

            # Assert failover happened within reasonable time (typically under 10 seconds)
            assert (
                failover_time < 10
            ), f"Failover took too long: {failover_time} seconds"
            assert new_master is not None, "No new master was elected"

        finally:
            # Ensure master container is restarted
            master_container.start()
            # Wait for cluster to stabilize
            time.sleep(5)

    def test_client_reconnection(
        self, redis_sentinel: Sentinel, redis_config, docker_client: docker.DockerClient
    ):
        """Test that clients can reconnect after failover"""
        # Get a master connection through sentinel
        master = redis_sentinel.master_for(
            redis_config["master_name"], decode_responses=True
        )

        # Write initial data
        assert master.set("reconnect_test", "before_failover")

        # Trigger failover by stopping current master
        master_container = docker_client.containers.get("redis-redis-master-1")
        master_container.stop()

        try:
            # Wait for failover and verify we can still write
            time.sleep(5)
            assert master.set("reconnect_test", "after_failover")
            assert master.get("reconnect_test") == "after_failover"

        finally:
            # Cleanup
            master_container.start()
