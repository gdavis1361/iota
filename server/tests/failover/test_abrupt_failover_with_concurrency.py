import asyncio
import logging
import subprocess
import time
from typing import Dict, Tuple

from redis.sentinel import Sentinel

import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConcurrentWriter:
    """Concurrent writer for Redis master with failover support."""

    def __init__(self):
        # Use Docker container IPs instead of localhost
        self.sentinel = Sentinel(
            [
                ("172.19.0.4", 26379),  # sentinel1
                ("172.19.0.5", 26379),  # sentinel2
                ("172.19.0.6", 26379),  # sentinel3
            ],
            socket_timeout=1.0,
            sentinel_kwargs={"socket_timeout": 1.0},
        )  # Increased timeout for better reliability
        self.master_name = "mymaster"
        self.write_interval = 0.1  # seconds between writes
        self.stats = {"success": 0, "fail": 0}
        self.running = False

    async def write_loop(self, duration: int = 30) -> Dict[str, int]:
        """
        Run a continuous write loop for the specified duration.

        Args:
            duration: How long to run the write loop in seconds

        Returns:
            Dict with success and failure counts
        """
        self.running = True
        start_time = time.time()
        key_counter = 0

        while time.time() - start_time < duration and self.running:
            try:
                # Get a fresh master connection each time to handle failovers
                master = self.sentinel.master_for(
                    self.master_name,
                    socket_timeout=1.0,  # Increased timeout
                    redis_class=redis.Redis,
                )
                key = f"concurrent_key_{key_counter}"
                value = f"value_{int(time.time())}"
                master.set(key, value)
                self.stats["success"] += 1
                key_counter += 1

                logger.debug(f"Write success: {key}={value}")
                await asyncio.sleep(self.write_interval)

            except redis.ConnectionError as e:
                logger.warning(f"Connection failed: {e}")
                self.stats["fail"] += 1
                await asyncio.sleep(1.0)  # Increased backoff during connection issues

            except redis.ReadOnlyError:
                logger.warning("Connected to replica instead of master, retrying...")
                self.stats["fail"] += 1
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Write failed: {e}")
                self.stats["fail"] += 1
                await asyncio.sleep(0.5)

        self.running = False
        return self.stats

    def stop(self):
        """Stop the write loop."""
        self.running = False


class RedisFailoverTest:
    """Test orchestrator for Redis Sentinel failover scenarios."""

    def __init__(self):
        self.compose_file = "docker-compose.redis.yml"
        self.network_name = "redis_redis-net"

    def _run_command(self, command: str) -> Tuple[int, str, str]:
        """
        Run a shell command and return its output.

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        except subprocess.SubProcessError as e:
            logger.error(f"Command failed: {e}")
            return 1, "", str(e)

    def kill_master(self) -> bool:
        """Abruptly kill the master container."""
        logger.info("Killing master container...")
        cmd = f"docker compose -f {self.compose_file} kill redis-master"
        code, out, err = self._run_command(cmd)
        return code == 0

    def start_master(self) -> bool:
        """Start the master container."""
        logger.info("Starting master container...")
        cmd = f"docker compose -f {self.compose_file} start redis-master"
        code, out, err = self._run_command(cmd)
        return code == 0

    def get_sentinel_logs(self, lines: int = 50) -> str:
        """Get recent sentinel logs."""
        cmd = f"docker compose -f {self.compose_file} logs --tail={lines} sentinel1"
        _, out, _ = self._run_command(cmd)
        return out

    def verify_master_role(self) -> Tuple[str, int]:
        """
        Get current master info from sentinel.

        Returns:
            Tuple of (ip, port) for current master
        """
        max_retries = 3
        retry_delay = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                sentinel = Sentinel(
                    [
                        ("172.19.0.4", 26379),
                        ("172.19.0.5", 26379),
                        ("172.19.0.6", 26379),
                    ],
                    socket_timeout=1.0,
                    sentinel_kwargs={"socket_timeout": 1.0},
                )

                # Try to get master info
                master_info = sentinel.discover_master("mymaster")

                # Verify we can connect to the master
                master = sentinel.master_for(
                    "mymaster", socket_timeout=1.0, redis_class=redis.Redis
                )
                if master.ping():
                    return master_info
                else:
                    raise redis.ConnectionError("Master ping failed")

            except (redis.ConnectionError, redis.ReadOnlyError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    time.sleep(retry_delay)
                else:
                    raise redis.ConnectionError(
                        "Failed to verify master after " f"{max_retries} attempts: {last_error}"
                    )


async def run_abrupt_failover_test():
    """Run the complete abrupt failover test with concurrent writes."""

    test = RedisFailoverTest()
    writer = ConcurrentWriter()

    try:
        # 1. Get initial master info
        initial_master_host, initial_master_port = test.verify_master_role()
        logger.info(f"Initial master: {initial_master_host}:{initial_master_port}")

        # 2. Start concurrent writes
        logger.info("Starting concurrent writes...")
        write_task = asyncio.create_task(writer.write_loop(30))

        # Let writes run for a few seconds before proceeding
        await asyncio.sleep(3)

        # 3. Kill master if it's the original master
        if initial_master_host == "172.19.0.2":
            logger.info("Killing original master...")
            test.kill_master()
        else:
            logger.info("Using already failed-over master, continuing test...")

        # 4. Wait for failover
        await asyncio.sleep(5)

        # 5. Verify new master
        new_master_host, new_master_port = test.verify_master_role()
        logger.info(f"New master: {new_master_host}:{new_master_port}")

        if new_master_host == initial_master_host:
            logger.error("Failover did not occur!")
            return False

        # 6. Wait for remaining writes
        write_stats = await write_task
        logger.info(f"Write stats during failover: {write_stats}")

        # 7. Verify we can still write to the new master
        sentinel = Sentinel(
            [("172.19.0.4", 26379), ("172.19.0.5", 26379), ("172.19.0.6", 26379)],
            socket_timeout=1.0,
        )

        master = sentinel.master_for("mymaster", socket_timeout=1.0)
        test_key = "failover_test_final"
        master.set(test_key, "success")
        result = master.get(test_key)
        logger.info(f"Final write test: {result == b'success'}")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        writer.stop()


if __name__ == "__main__":
    asyncio.run(run_abrupt_failover_test())
