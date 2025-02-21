import asyncio
import logging
import time
from typing import Dict, List

import redis.asyncio as redis
from redis.sentinel import Sentinel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NetworkPartitionTest:
    """Test orchestrator for Redis Sentinel network partition scenarios."""

    def __init__(self):
        self.sentinel = Sentinel(
            [("172.19.0.4", 26379), ("172.19.0.5", 26379), ("172.19.0.6", 26379)],
            socket_timeout=1.0,
        )

    def simulate_master_failure(self) -> bool:
        """Simulate master failure using Redis SHUTDOWN command."""
        try:
            logger.info("Shutting down master...")
            master_host, master_port = self.sentinel.discover_master("mymaster")
            redis_client = redis.Redis(
                host=master_host, port=master_port, socket_timeout=1.0
            )
            redis_client.shutdown(nosave=True)
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown master: {e}")
            return False

    def get_sentinel_info(self) -> List[str]:
        """Get sentinel info about the master and replicas from all sentinels."""
        info_list = []
        for port in [26379, 26380, 26381]:
            try:
                sentinel = redis.Redis(host="172.19.0.4", port=port)
                info = sentinel.info("sentinel")
                info_list.append(f"Sentinel {port}: {info}")
            except Exception as e:
                logger.error(f"Failed to get sentinel info from port {port}: {e}")
        return info_list


class PartitionScenario:
    """Manages network partition scenarios and metrics collection."""

    def __init__(self):
        self.test = NetworkPartitionTest()
        self.metrics = {
            "start_time": time.time(),
            "events": [],
            "write_stats": {"success": 0, "fail": 0},
        }

    def record_event(self, event_type: str, details: str = None):
        """Record a timestamped event."""
        self.metrics["events"].append(
            {"timestamp": time.time(), "type": event_type, "details": details}
        )

    async def run_master_partition_test(self):
        """
        Test scenario: Master failure
        1. Shutdown master using Redis command
        2. Verify sentinel promotes replica
        3. Verify replica becomes new master
        4. Verify writes continue to new master
        """
        try:
            # 1. Initial state
            self.record_event("test_start", "Master failure test")
            initial_master = self.test.sentinel.discover_master("mymaster")
            self.record_event("initial_state", f"Initial master: {initial_master}")

            # 2. Start concurrent writes
            writer = ConcurrentWriter(self)
            write_task = asyncio.create_task(writer.write_loop(30))

            await asyncio.sleep(3)  # Allow writes to stabilize

            # 3. Shutdown master
            self.record_event("master_shutdown", "Shutting down master")
            if not self.test.simulate_master_failure():
                raise Exception("Failed to shutdown master")

            # 4. Wait for failover
            await asyncio.sleep(5)

            # 5. Verify new master
            try:
                new_master = self.test.sentinel.discover_master("mymaster")
                self.record_event("failover_complete", f"New master: {new_master}")

                if new_master == initial_master:
                    self.record_event("failover_failed", "Master unchanged")
                    return False
            except Exception as e:
                self.record_event("master_discovery_error", str(e))
                return False

            # 6. Verify sentinel state
            sentinel_info = self.test.get_sentinel_info()
            for info in sentinel_info:
                self.record_event("sentinel_info", info)

            # 7. Complete test
            write_stats = await write_task
            self.metrics["write_stats"].update(write_stats)

            self.print_report()
            return True

        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.record_event("test_error", str(e))
            self.print_report()
            return False
        finally:
            writer.stop()

    def print_report(self):
        """Print a detailed metrics report."""
        print("\n=== Master Failure Test Report ===")
        print(f"Total Duration: {time.time() - self.metrics['start_time']:.2f}s")

        total_writes = (
            self.metrics["write_stats"]["success"] + self.metrics["write_stats"]["fail"]
        )
        if total_writes > 0:
            success_rate = (self.metrics["write_stats"]["success"] / total_writes) * 100
            print(f"Write Success Rate: {success_rate:.1f}%")

        print("\nEvent Timeline:")
        for event in self.metrics["events"]:
            relative_time = event["timestamp"] - self.metrics["start_time"]
            print(f"{relative_time:.3f}s - {event['type']}: {event['details'] or ''}")


class ConcurrentWriter:
    """Concurrent writer for Redis master with failover support."""

    def __init__(self, scenario: PartitionScenario):
        self.scenario = scenario
        self.sentinel = Sentinel(
            [("172.19.0.4", 26379), ("172.19.0.5", 26379), ("172.19.0.6", 26379)],
            socket_timeout=1.0,
        )
        self.master_name = "mymaster"
        self.write_interval = 0.1
        self.running = False

    async def write_loop(self, duration: int = 30) -> Dict[str, int]:
        """Run a continuous write loop for the specified duration."""
        self.running = True
        start_time = time.time()
        key_counter = 0

        while time.time() - start_time < duration and self.running:
            try:
                master = self.sentinel.master_for(
                    self.master_name, socket_timeout=1.0, redis_class=redis.Redis
                )
                key = f"partition_test_key_{key_counter}"
                value = f"value_{int(time.time())}"

                write_start = time.time()
                master.set(key, value)
                write_duration = time.time() - write_start

                self.scenario.metrics["write_stats"]["success"] += 1
                if write_duration > 0.1:
                    self.scenario.record_event("slow_write", f"{write_duration:.3f}s")

                key_counter += 1
                await asyncio.sleep(self.write_interval)

            except redis.ConnectionError as e:
                self.scenario.metrics["write_stats"]["fail"] += 1
                self.scenario.record_event("write_error", str(e))
                await asyncio.sleep(1.0)

            except redis.ReadOnlyError:
                self.scenario.metrics["write_stats"]["fail"] += 1
                self.scenario.record_event("readonly_error")
                await asyncio.sleep(0.5)

            except Exception as e:
                self.scenario.metrics["write_stats"]["fail"] += 1
                self.scenario.record_event("write_error", str(e))
                await asyncio.sleep(0.5)

        self.running = False
        return self.scenario.metrics["write_stats"]

    def stop(self):
        """Stop the write loop."""
        self.running = False


async def run_partition_tests():
    """Run all network partition test scenarios."""
    scenario = PartitionScenario()
    await scenario.run_master_partition_test()


if __name__ == "__main__":
    asyncio.run(run_partition_tests())
