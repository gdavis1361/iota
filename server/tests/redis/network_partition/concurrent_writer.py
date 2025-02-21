import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WriteMetrics:
    """Metrics for write operations"""

    successful_writes: int = 0
    failed_writes: int = 0
    total_latency: float = 0.0

    @property
    def total_writes(self) -> int:
        return self.successful_writes + self.failed_writes

    @property
    def average_latency(self) -> float:
        return (
            self.total_latency / self.successful_writes
            if self.successful_writes > 0
            else 0
        )

    @property
    def success_rate(self) -> float:
        return (
            (self.successful_writes / self.total_writes * 100)
            if self.total_writes > 0
            else 0
        )


class ConcurrentWriter:
    """Performs concurrent write operations to Redis with metrics collection"""

    def __init__(
        self, host: str = "localhost", port: int = 6381, write_interval: float = 0.1
    ):
        self.host = host
        self.port = port
        self.write_interval = write_interval
        self.client: Optional[redis.Redis] = None
        self.metrics = WriteMetrics()
        self.is_running = False

    async def connect(self):
        """Establish Redis connection"""
        self.client = redis.Redis(
            host=self.host, port=self.port, socket_timeout=1, retry_on_timeout=True
        )
        try:
            await asyncio.to_thread(self.client.ping)
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def write_key(self, key: str, value: str) -> bool:
        """Write a single key-value pair to Redis"""
        start_time = time.time()
        try:
            await asyncio.to_thread(self.client.set, key, value)
            latency = time.time() - start_time
            self.metrics.successful_writes += 1
            self.metrics.total_latency += latency
            return True
        except redis.RedisError as e:
            logger.error(f"Write failed for key {key}: {e}")
            self.metrics.failed_writes += 1
            return False

    async def continuous_write(self):
        """Continuously write keys to Redis"""
        counter = 0
        while self.is_running:
            key = f"test_key_{int(time.time())}_{counter}"
            value = f"value_{counter}"
            await self.write_key(key, value)
            counter += 1
            await asyncio.sleep(self.write_interval)

    async def start(self):
        """Start the continuous write process"""
        await self.connect()
        self.is_running = True
        logger.info("Starting continuous write operations")
        await self.continuous_write()

    def stop(self):
        """Stop the continuous write process"""
        self.is_running = False
        if self.client:
            self.client.close()
        logger.info("Stopped write operations")

    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return {
            "successful_writes": self.metrics.successful_writes,
            "failed_writes": self.metrics.failed_writes,
            "total_writes": self.metrics.total_writes,
            "success_rate": self.metrics.success_rate,
            "average_latency": self.metrics.average_latency,
        }
