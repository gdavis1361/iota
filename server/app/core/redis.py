import logging
from typing import Optional

from app.core.config import settings
from app.core.logging_config import diagnostics
from redis.asyncio import ConnectionPool, Redis

logger = logging.getLogger(__name__)

# Global Redis pool and client
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None


def record_metrics(name: str, value: float, tags: Optional[dict] = None):
    """Record metrics with error handling"""
    try:
        if hasattr(diagnostics, "metrics") and hasattr(diagnostics.metrics, "record"):
            diagnostics.metrics.record(name, value, tags or {})
    except Exception as e:
        logger.debug(f"Failed to record metrics for {name}: {str(e)}")


async def init_redis_pool() -> Redis:
    """Initialize Redis connection pool and return a Redis client"""
    global redis_pool, redis_client

    if redis_pool is None:
        try:
            logger.info(f"Initializing Redis pool for {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
            redis_client = Redis(connection_pool=redis_pool)
            # Test the connection
            await redis_client.ping()
            logger.info("Redis pool initialized successfully")
            record_metrics("redis_pool_init", 1, {"status": "success"})
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {str(e)}")
            record_metrics("redis_pool_init", 0, {"status": "failure"})
            redis_pool = None
            redis_client = None
            raise
    elif redis_client is None:
        redis_client = Redis(connection_pool=redis_pool)

    return redis_client


def get_redis_client() -> Redis:
    """Get Redis client with connection pooling"""
    global redis_client

    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis_pool() first.")

    return redis_client


async def close_redis_client():
    """Close Redis client and pool connections"""
    global redis_client, redis_pool

    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis client closed successfully")
            record_metrics("redis_client_close", 1, {"status": "success"})
        except Exception as e:
            logger.error(f"Failed to close Redis client: {str(e)}")
            record_metrics("redis_client_close", 0, {"status": "failure"})
        finally:
            redis_client = None

    if redis_pool:
        try:
            await redis_pool.disconnect()
            logger.info("Redis pool closed successfully")
            record_metrics("redis_pool_close", 1, {"status": "success"})
        except Exception as e:
            logger.error(f"Failed to close Redis pool: {str(e)}")
            record_metrics("redis_pool_close", 0, {"status": "failure"})
        finally:
            redis_pool = None
