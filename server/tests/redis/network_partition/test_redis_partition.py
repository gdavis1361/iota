import asyncio
import logging
from typing import List, Tuple

import docker
import pytest
import redis.sentinel
from docker.models.containers import Container
from docker.models.networks import Network

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestNetworkPartition:
    @pytest.fixture(scope="class")
    def docker_client(self):
        return docker.from_env()

    @pytest.fixture(scope="class")
    def redis_network(self, docker_client) -> Network:
        """Get the Redis network"""
        return docker_client.networks.get("redis_redis-net")

    @pytest.fixture(scope="class")
    def containers(self, docker_client) -> Tuple[Container, Container, List[Container]]:
        """Get Redis master, replica, and sentinel containers"""
        master = docker_client.containers.get("redis-redis-master-1")
        replica = docker_client.containers.get("redis-redis-replica-1")
        sentinels = [
            docker_client.containers.get(f"redis-redis-sentinel-{i}-1")
            for i in range(1, 4)
        ]
        return master, replica, sentinels

    @pytest.fixture(scope="class")
    def sentinel_clients(self) -> List[redis.sentinel.Sentinel]:
        """Create Redis Sentinel clients"""
        sentinels = [(f"localhost", 26379 + i) for i in range(3)]
        return [
            redis.sentinel.Sentinel(
                sentinels, socket_timeout=0.1, retry_on_timeout=True
            )
            for _ in range(3)
        ]

    async def _wait_for_failover(
        self, sentinel_client: redis.sentinel.Sentinel, timeout: int = 30
    ):
        """Wait for failover to complete"""
        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                master = sentinel_client.discover_master("mymaster")
                logger.info("Current master: " + str(master))
                return master
            except redis.sentinel.MasterNotFoundError:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError("Failover did not complete in time")
                await asyncio.sleep(1)

    def test_sentinel_partition_from_master(
        self, redis_network, containers, sentinel_clients
    ):
        """Test scenario where one sentinel is partitioned from master"""
        master, _, sentinels = containers
        sentinel = sentinels[0]

        # Record initial master
        original_master = sentinel_clients[0].discover_master("mymaster")
        logger.info("Original master: " + str(original_master))

        try:
            # Disconnect first sentinel from network
            sentinel = sentinels[0]
            logger.info("Disconnecting sentinel from network")
            redis_network.disconnect(sentinel)
            logger.info("Disconnected sentinel from network")

            # No failover should occur as other sentinels can still see master
            new_master = sentinel_clients[1].discover_master("mymaster")
            assert (
                new_master == original_master
            ), "Master should not change when only one sentinel is partitioned"

        finally:
            # Reconnect sentinel
            redis_network.connect(sentinel, "redis-net")
            logger.info("Reconnected sentinel to network")

    def test_master_partition_from_all_sentinels(
        self, redis_network, containers, sentinel_clients
    ):
        """Test scenario where master is partitioned from all sentinels"""
        master, replica, _ = containers

        # Record initial master
        original_master = sentinel_clients[0].discover_master("mymaster")
        logger.info("Original master: " + str(original_master))

        try:
            # Disconnect master from network
            redis_network.disconnect(master)
            logger.info("Disconnected master from network")

            # Wait for failover to complete
            asyncio.run(self._wait_for_failover(sentinel_clients[0]))

            # Verify new master is different
            new_master = sentinel_clients[0].discover_master("mymaster")
            assert (
                new_master != original_master
            ), "Failover should occur when master is partitioned"

        finally:
            # Reconnect master
            redis_network.connect(master, "redis-net")
            logger.info("Reconnected master to network")

    def test_replica_partition_from_master(
        self, redis_network, containers, sentinel_clients
    ):
        """Test scenario where replica is partitioned from master"""
        master, replica, _ = containers

        # Record initial master
        original_master = sentinel_clients[0].discover_master("mymaster")
        logger.info("Original master: " + str(original_master))

        try:
            # Disconnect replica from network
            redis_network.disconnect(replica)
            logger.info("Disconnected replica from network")

            # No failover should occur as master is still healthy
            new_master = sentinel_clients[0].discover_master("mymaster")
            assert (
                new_master == original_master
            ), "Master should not change when replica is partitioned"

        finally:
            # Reconnect replica
            redis_network.connect(replica, "redis-net")
            logger.info("Reconnected replica to network")

    def test_split_brain_prevention(self, redis_network, containers, sentinel_clients):
        """Test prevention of split-brain scenario"""
        master, replica, sentinels = containers

        # Record initial master
        original_master = sentinel_clients[0].discover_master("mymaster")
        logger.info("Original master: " + str(original_master))

        try:
            # Create network partition by disconnecting half of sentinels
            for sentinel in sentinels[:2]:
                redis_network.disconnect(sentinel)
            logger.info("Created network partition between sentinels")

            # No failover should occur as quorum cannot be reached
            new_master = sentinel_clients[2].discover_master("mymaster")
            assert (
                new_master == original_master
            ), "Split-brain: Master changed without quorum"

        finally:
            # Reconnect all sentinels
            for sentinel in sentinels[:2]:
                redis_network.connect(sentinel, "redis-net")
            logger.info("Reconnected all sentinels")
