"""Redis Network Partition Tests.

This module contains tests that simulate various network partition scenarios
in a Redis Sentinel environment.
"""

import os
import time
from typing import Generator, List, Tuple

import docker
import pytest
import redis
from redis.sentinel import Sentinel


@pytest.fixture(scope="module")
def docker_client() -> Generator[docker.DockerClient, None, None]:
    """Create a Docker client for container management during tests."""
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture(scope="module")
def sentinel_clients() -> List[Sentinel]:
    """Create connections to all sentinel instances."""
    sentinel_ports = [26380, 26381, 26382]
    return [
        Sentinel(
            [(os.getenv("REDIS_SENTINEL_HOST", "localhost"), port)],
            socket_timeout=1.0,
            password=os.getenv("REDIS_PASSWORD"),
            sentinel_kwargs={"password": os.getenv("REDIS_PASSWORD")},
        )
        for port in sentinel_ports
    ]


@pytest.fixture(scope="function")
def network_cleanup(docker_client: docker.DockerClient) -> Generator[None, None, None]:
    """Ensure all containers are connected to the network after each test."""
    yield
    network = docker_client.networks.get("redis_redis-net")
    containers = [
        "redis-redis-master-1",
        "redis-redis-replica-1",
        "redis-redis-sentinel-1-1",
        "redis-redis-sentinel-2-1",
        "redis-redis-sentinel-3-1",
    ]

    for container_name in containers:
        try:
            container = docker_client.containers.get(container_name)
            try:
                network.connect(container)
            except docker.errors.APIError:
                # Container already connected
                pass
        except docker.errors.NotFound:
            continue


@pytest.mark.redis
@pytest.mark.redis_sentinel
class TestNetworkPartition:
    """Test suite for network partition scenarios."""

    def _wait_for_failover(
        self, sentinel: Sentinel, timeout: int = 30
    ) -> Tuple[str, int]:
        """Wait for failover to complete and return new master."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                return sentinel.discover_master("mymaster")
            except redis.sentinel.MasterNotFoundError:
                time.sleep(0.1)
        raise TimeoutError("Failover did not complete within timeout")

    def _verify_write_to_master(self, sentinel: Sentinel, key: str, value: str) -> bool:
        """Verify we can write to and read from the current master."""
        try:
            master = sentinel.master_for("mymaster", socket_timeout=1.0)
            return master.set(key, value) and master.get(key) == value
        except (redis.ConnectionError, redis.TimeoutError):
            return False

    @pytest.mark.timeout(60)
    def test_sentinel_partition_from_master(
        self,
        docker_client: docker.DockerClient,
        sentinel_clients: List[Sentinel],
        network_cleanup: None,
    ):
        """Test scenario where one sentinel loses connection to master."""
        # Initial state verification
        original_master = sentinel_clients[0].discover_master("mymaster")

        try:
            # Disconnect sentinel-1 from network
            network = docker_client.networks.get("redis_redis-net")
            sentinel_container = docker_client.containers.get(
                "redis-redis-sentinel-1-1"
            )
            network.disconnect(sentinel_container)

            # Wait and verify no failover occurs (other sentinels still see master)
            time.sleep(15)  # Increased wait time

            # Check with second sentinel that master hasn't changed
            current_master = sentinel_clients[1].discover_master("mymaster")
            assert (
                current_master == original_master
            ), "Failover occurred when it shouldn't have"

            # Verify we can still write to master
            assert self._verify_write_to_master(
                sentinel_clients[1], "partition_test_key", "test_value"
            ), "Cannot write to master"

        finally:
            # Cleanup
            try:
                network.connect(sentinel_container)
            except docker.errors.APIError:
                pass
            time.sleep(5)

    @pytest.mark.timeout(60)
    def test_master_partition_from_all_sentinels(
        self,
        docker_client: docker.DockerClient,
        sentinel_clients: List[Sentinel],
        network_cleanup: None,
    ):
        """Test scenario where master is isolated from all sentinels."""
        # Initial state verification
        original_master = sentinel_clients[0].discover_master("mymaster")

        try:
            # Disconnect master from network
            network = docker_client.networks.get("redis_redis-net")
            master_container = docker_client.containers.get("redis-redis-master-1")
            network.disconnect(master_container)

            # Wait for failover
            time.sleep(15)  # Increased wait time
            new_master = self._wait_for_failover(sentinel_clients[0])

            # Verify failover occurred
            assert new_master != original_master, "Failover did not occur"

            # Verify we can write to new master
            assert self._verify_write_to_master(
                sentinel_clients[0], "new_master_test_key", "new_master_value"
            ), "Cannot write to new master"

        finally:
            # Cleanup
            try:
                network.connect(master_container)
            except docker.errors.APIError:
                pass
            time.sleep(5)

    @pytest.mark.timeout(60)
    def test_replica_partition_from_master(
        self,
        docker_client: docker.DockerClient,
        sentinel_clients: List[Sentinel],
        network_cleanup: None,
    ):
        """Test scenario where replica loses connection to master."""
        # Initial state verification
        original_master = sentinel_clients[0].discover_master("mymaster")

        try:
            # Disconnect replica from network
            network = docker_client.networks.get("redis_redis-net")
            replica_container = docker_client.containers.get("redis-redis-replica-1")
            network.disconnect(replica_container)

            # Wait and verify no failover occurs
            time.sleep(15)  # Increased wait time

            # Check master hasn't changed
            current_master = sentinel_clients[0].discover_master("mymaster")
            assert current_master == original_master, "Unexpected failover occurred"

            # Verify we can still write to master
            assert self._verify_write_to_master(
                sentinel_clients[0], "replica_partition_test_key", "test_value"
            ), "Cannot write to master"

        finally:
            # Cleanup
            try:
                network.connect(replica_container)
            except docker.errors.APIError:
                pass
            time.sleep(5)

    @pytest.mark.timeout(90)
    def test_split_brain_prevention(
        self,
        docker_client: docker.DockerClient,
        sentinel_clients: List[Sentinel],
        network_cleanup: None,
    ):
        """Test prevention of split-brain scenario with partial sentinel isolation."""
        # Initial state verification
        original_master = sentinel_clients[0].discover_master("mymaster")

        try:
            # Disconnect sentinel-2 from network
            network = docker_client.networks.get("redis_redis-net")
            sentinel2 = docker_client.containers.get("redis-redis-sentinel-2-1")
            network.disconnect(sentinel2)

            # Verify no failover with single sentinel partition
            time.sleep(15)  # Increased wait time
            current_master = sentinel_clients[0].discover_master("mymaster")
            assert current_master == original_master, "Unexpected failover occurred"

            # Disconnect sentinel-3 as well
            sentinel3 = docker_client.containers.get("redis-redis-sentinel-3-1")
            network.disconnect(sentinel3)

            # Verify still no failover (not enough sentinels to reach quorum)
            time.sleep(15)  # Increased wait time
            current_master = sentinel_clients[0].discover_master("mymaster")
            assert current_master == original_master, "Failover occurred without quorum"

        finally:
            # Cleanup
            try:
                network.connect(sentinel2)
                network.connect(sentinel3)
            except docker.errors.APIError:
                pass
            time.sleep(5)
