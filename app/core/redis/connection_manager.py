"""Redis connection management with resilience patterns."""
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional, TypeVar

import backoff
from redis.exceptions import ConnectionError, TimeoutError
from redis.sentinel import Sentinel

from app.core.config import settings
from app.core.metrics import record_metric
from redis import Redis, RedisError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.is_open = False
        self._last_failure_time = 0

    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            self._last_failure_time = time.time()
            logger.warning("Circuit breaker opened due to multiple failures")

    def record_success(self):
        """Record a success and reset failure count."""
        self.failure_count = 0
        self.is_open = False

    def should_allow_request(self) -> bool:
        """Check if request should be allowed through."""
        if not self.is_open:
            return True
        if time.time() - self._last_failure_time >= self.reset_timeout:
            logger.info("Circuit breaker reset timeout reached, allowing request")
            return True
        return False


class RedisConnectionManager:
    """Manages Redis connections with resilience patterns."""

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._connection_pool = None
        self._sentinel = None
        self._master = None

    @backoff.on_exception(backoff.expo, (ConnectionError, TimeoutError), max_tries=3)
    async def get_connection(self) -> Redis:
        """Get a Redis connection with retries and circuit breaker."""
        if not self.circuit_breaker.should_allow_request():
            raise RedisError("Circuit breaker is open")

        try:
            if not self._master:
                self._sentinel = Sentinel(
                    [(settings.REDIS_HOST, settings.REDIS_PORT)], socket_timeout=1.0
                )
                self._master = self._sentinel.master_for(
                    "mymaster", socket_timeout=1.0, password=settings.REDIS_PASSWORD
                )

            # Test connection
            self._master.ping()
            self.circuit_breaker.record_success()
            record_metric("redis.connection.success", 1)
            return self._master

        except (ConnectionError, TimeoutError) as e:
            self.circuit_breaker.record_failure()
            record_metric("redis.connection.failure", 1)
            logger.error(f"Redis connection error: {str(e)}")
            raise

    @asynccontextmanager
    async def connection(self) -> Redis:
        """Context manager for Redis connections."""
        conn = None
        try:
            conn = await self.get_connection()
            yield conn
        finally:
            if conn:
                await conn.close()

    async def execute_with_retry(
        self, operation: str, command_fn: Any, *args: Any, **kwargs: Any
    ) -> T:
        """Execute Redis command with retry logic."""
        async with self.connection() as redis:
            try:
                result = await command_fn(redis, *args, **kwargs)
                record_metric(f"redis.operation.{operation}.success", 1)
                return result
            except RedisError as e:
                record_metric(f"redis.operation.{operation}.failure", 1)
                logger.error(f"Redis operation {operation} failed: {str(e)}")
                raise


# Global connection manager instance
redis_manager = RedisConnectionManager()
