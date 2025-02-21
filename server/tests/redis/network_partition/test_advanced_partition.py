"""Advanced Redis Sentinel partition tests."""

import asyncio
import logging

import pytest

logger = logging.getLogger(__name__)


class TestAdvancedPartition:
    """Test advanced Redis Sentinel partition scenarios."""

    @pytest.mark.asyncio
    async def test_partial_sentinel_isolation(
        self, redis_network, containers, sentinel_clients, writer
    ):
        """Test behavior when a single sentinel is isolated."""
        master, replica, sentinels = containers

        # Start concurrent writes
        write_task = asyncio.create_task(writer.start())
        await asyncio.sleep(2)  # Allow some writes to occur

        try:
            # Record initial state
            original_master = sentinel_clients[0].discover_master("mymaster")
            logger.info(f"Original master: {original_master}")

            # Isolate first sentinel
            redis_network.disconnect(sentinels[0])
            logger.info("Disconnected sentinel1 from network")

            # Wait and verify no failover occurs
            await asyncio.sleep(10)
            current_master = sentinel_clients[1].discover_master("mymaster")

            # Verify master hasn't changed
            assert (
                current_master == original_master
            ), "Master should not change when only one sentinel is partitioned"

            # Check write metrics
            metrics = writer.get_metrics()
            logger.info(f"Write metrics during sentinel isolation: {metrics}")
            assert (
                metrics["success_rate"] > 95
            ), "Write success rate should remain high during sentinel isolation"

        finally:
            # Cleanup
            writer.stop()
            write_task.cancel()
            try:
                await write_task
            except asyncio.CancelledError:
                pass

            redis_network.connect(sentinels[0], "redis_redis-net")
            logger.info("Reconnected sentinel to network")

    @pytest.mark.asyncio
    async def test_split_brain_prevention(
        self, redis_network, containers, sentinel_clients, writer
    ):
        """Test split-brain prevention by creating a network partition that separates:
        - Group 1: sentinel1 + master
        - Group 2: sentinel2 + sentinel3 + replica

        Even though Group 2 has more sentinels, failover should not occur without
        proper quorum agreement about master state.
        """
        master, replica, sentinels = containers

        # Start concurrent writes
        write_task = asyncio.create_task(writer.start())
        await asyncio.sleep(2)

        try:
            # Record initial state
            original_master = sentinel_clients[0].discover_master("mymaster")
            logger.info(f"Original master: {original_master}")

            # Create split-brain scenario
            # Group 1: sentinel1 + master
            for sentinel in sentinels[1:]:  # sentinel2 and sentinel3
                redis_network.disconnect(sentinel)
                logger.info(f"Disconnected {sentinel.name} from master")

            # Group 2: sentinel2 + sentinel3 + replica
            redis_network.disconnect(replica)
            logger.info("Disconnected replica from master")

            # Wait and verify no failover occurs
            await asyncio.sleep(10)

            try:
                current_master = sentinel_clients[0].discover_master("mymaster")
                assert (
                    current_master == original_master
                ), "Split-brain: Master changed without proper quorum"
            except Exception as e:
                logger.error(f"Error checking master status: {e}")
                raise

            # Check write metrics
            metrics = writer.get_metrics()
            logger.info(f"Write metrics during split-brain scenario: {metrics}")

        finally:
            # Cleanup
            writer.stop()
            write_task.cancel()
            try:
                await write_task
            except asyncio.CancelledError:
                pass

            # Reconnect all nodes
            for sentinel in sentinels[1:]:
                redis_network.connect(sentinel, "redis_redis-net")
            redis_network.connect(replica, "redis_redis-net")
            logger.info("Reconnected all nodes to network")

    @pytest.mark.asyncio
    async def test_majority_partition_failover(
        self, redis_network, containers, sentinel_clients, writer
    ):
        """Test proper failover when a majority of sentinels (2 out of 3) agree
        that the master is down, while maintaining write operations.
        """
        master, replica, sentinels = containers

        # Start concurrent writes
        write_task = asyncio.create_task(writer.start())
        await asyncio.sleep(2)

        try:
            # Record initial state
            original_master = sentinel_clients[0].discover_master("mymaster")
            logger.info(f"Original master: {original_master}")

            # Disconnect master from majority of sentinels
            for sentinel in sentinels[:2]:  # sentinel1 and sentinel2
                redis_network.disconnect(sentinel)
                logger.info(f"Disconnected {sentinel.name} from master")

            # Wait for failover
            await self._wait_for_failover(sentinel_clients[2])
            logger.info("Failover completed")

            # Verify new master
            new_master = sentinel_clients[2].discover_master("mymaster")
            assert (
                new_master != original_master
            ), "Failover should occur when majority of sentinels cannot see master"

            # Check write metrics
            metrics = writer.get_metrics()
            logger.info(f"Write metrics during majority partition: {metrics}")
            assert (
                metrics["success_rate"] > 90
            ), "Write success rate should recover after failover"

        finally:
            # Cleanup
            writer.stop()
            write_task.cancel()
            try:
                await write_task
            except asyncio.CancelledError:
                pass

            # Reconnect all nodes
            for sentinel in sentinels[:2]:
                redis_network.connect(sentinel, "redis_redis-net")
            logger.info("Reconnected all nodes to network")
