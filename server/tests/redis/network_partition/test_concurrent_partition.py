import asyncio
import logging

import pytest
from concurrent_writer import ConcurrentWriter
from test_redis_partition import TestNetworkPartition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConcurrentPartition(TestNetworkPartition):
    @pytest.fixture(scope="class")
    async def writer(self):
        """Create and manage ConcurrentWriter instance"""
        writer = ConcurrentWriter(host="localhost", port=6381, write_interval=0.1)
        yield writer
        writer.stop()

    @pytest.mark.asyncio
    async def test_master_partition_with_writes(
        self, redis_network, containers, sentinel_clients, writer
    ):
        """Test master partition while performing concurrent writes"""
        master, replica, _ = containers

        # Record initial master
        original_master = sentinel_clients[0].discover_master("mymaster")
        logger.info(f"Original master: {original_master}")

        # Start concurrent writes
        write_task = asyncio.create_task(writer.start())
        await asyncio.sleep(2)  # Allow some writes to occur

        try:
            # Partition master
            redis_network.disconnect(master)
            logger.info("Disconnected master from network")

            # Wait for failover
            await self._wait_for_failover(sentinel_clients[0])
            logger.info("Failover completed")

            # Continue writes for a bit
            await asyncio.sleep(5)

            # Get current metrics
            metrics = writer.get_metrics()
            logger.info(f"Write metrics during partition: {metrics}")

            # Verify new master
            new_master = sentinel_clients[0].discover_master("mymaster")
            assert new_master != original_master, "Failover should have occurred"

            # Success criteria
            assert (
                metrics["success_rate"] > 90
            ), "Write success rate should be above 90%"
            assert (
                metrics["average_latency"] < 0.1
            ), "Average write latency should be under 100ms"

        finally:
            # Cleanup
            writer.stop()
            write_task.cancel()
            try:
                await write_task
            except asyncio.CancelledError:
                pass

            redis_network.connect(master, "redis_redis-net")
            logger.info("Reconnected master to network")

    @pytest.mark.asyncio
    async def test_replica_partition_with_writes(
        self, redis_network, containers, sentinel_clients, writer
    ):
        """Test replica partition while performing concurrent writes"""
        master, replica, _ = containers

        # Record initial master
        original_master = sentinel_clients[0].discover_master("mymaster")
        logger.info(f"Original master: {original_master}")

        # Start concurrent writes
        write_task = asyncio.create_task(writer.start())
        await asyncio.sleep(2)  # Allow some writes to occur

        try:
            # Partition replica
            redis_network.disconnect(replica)
            logger.info("Disconnected replica from network")

            # Continue writes for a bit
            await asyncio.sleep(5)

            # Get current metrics
            metrics = writer.get_metrics()
            logger.info(f"Write metrics during replica partition: {metrics}")

            # Verify master hasn't changed
            current_master = sentinel_clients[0].discover_master("mymaster")
            assert (
                current_master == original_master
            ), "Master should not change during replica partition"

            # Success criteria
            assert (
                metrics["success_rate"] > 95
            ), "Write success rate should be above 95%"
            assert (
                metrics["average_latency"] < 0.1
            ), "Average write latency should be under 100ms"

        finally:
            # Cleanup
            writer.stop()
            write_task.cancel()
            try:
                await write_task
            except asyncio.CancelledError:
                pass

            redis_network.connect(replica, "redis_redis-net")
            logger.info("Reconnected replica to network")
