import logging
import time
from functools import wraps
from typing import Callable, Optional, Tuple

from app.core.config import settings
from app.core.logging_config import diagnostics
from app.core.redis import get_redis_client
from fastapi import HTTPException, Request, Response

logger = logging.getLogger(__name__)


def record_metrics(name: str, value: float, tags: Optional[dict] = None):
    """Record metrics with error handling"""
    try:
        if hasattr(diagnostics, "metrics") and hasattr(diagnostics.metrics, "record"):
            diagnostics.metrics.record(name, value, tags or {})
    except Exception as e:
        logger.debug(f"Failed to record metrics for {name}: {str(e)}")


def get_client_ip(request: Request) -> str:
    """Get client IP from request, with fallback for test environment"""
    if not request:
        return "127.0.0.1"
    if not request.client:
        return request.headers.get("X-Forwarded-For", "127.0.0.1").split(",")[0]
    return request.client.host or "127.0.0.1"


async def check_rate_limit(
    request: Request, limit: int = None, window: int = None
) -> Tuple[bool, dict]:
    """
    Check if request is within rate limits
    Returns (is_allowed, rate_limit_info)
    """
    try:
        # Get client IP
        client_ip = get_client_ip(request)
        path = request.url.path

        # Use defaults if not specified
        limit = limit or settings.RATE_LIMIT_REQUESTS
        window = window or settings.RATE_LIMIT_WINDOW

        # Get Redis client
        try:
            redis = await get_redis_client()
        except Exception as e:
            logger.error(f"Failed to get Redis client: {str(e)}")
            return True, {}  # Allow request on Redis error

        if not redis:
            logger.warning("No Redis client available")
            return True, {}

        # Create unique key for this IP and endpoint
        key = f"rate_limit:{client_ip}:{path}"

        try:
            # Get current count
            current = await redis.get(key)
            current = int(current) if current else 0

            # Get TTL
            ttl = await redis.ttl(key)
            if ttl < 0:
                ttl = window

            # Check if over limit
            if current >= limit:
                record_metrics("rate_limit_exceeded", 1, {"path": path})
                return False, {
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + ttl)),
                }

            # Increment counter
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            await pipe.execute()

            record_metrics("rate_limit_request", 1, {"path": path})

            return True, {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(limit - current - 1),
                "X-RateLimit-Reset": str(int(time.time() + ttl)),
            }

        except Exception as e:
            logger.error(f"Redis operation failed: {str(e)}")
            return True, {}  # Allow request on Redis error

    except Exception as e:
        logger.error(f"Rate limit check failed: {str(e)}")
        return True, {}  # Allow request on general error


def rate_limit(calls: int, period: int):
    """
    Rate limit decorator for FastAPI endpoints

    Args:
        calls (int): Number of calls allowed
        period (int): Time period in seconds
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                return await func(*args, **kwargs)

            is_allowed, headers = await check_rate_limit(request, calls, period)

            if not is_allowed:
                raise HTTPException(status_code=429, detail="Too many requests", headers=headers)

            response = await func(*args, **kwargs)

            # If response is a Response object, add headers
            if isinstance(response, Response):
                for key, value in headers.items():
                    response.headers[key] = value

            return response

        return wrapper

    return decorator


def auth_rate_limit():
    """Rate limit for authentication endpoints (5 attempts per minute)"""
    return rate_limit(calls=5, period=60)


def api_rate_limit():
    """Standard API rate limit (60 requests per minute)"""
    return rate_limit(calls=60, period=60)


def heavy_operation_rate_limit():
    """Rate limit for resource-intensive operations (10 requests per minute)"""
    return rate_limit(calls=10, period=60)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    try:
        # Skip rate limiting for test environments if needed
        if settings.TESTING and not settings.RATE_LIMIT_TESTS:
            return await call_next(request)

        is_allowed, headers = await check_rate_limit(request)

        if not is_allowed:
            raise HTTPException(status_code=429, detail="Too many requests", headers=headers)

        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limit middleware error: {str(e)}")
        return await call_next(request)  # Allow request on error
