#!/usr/bin/env python3
"""Rate Limiting Module

Provides rate limiting functionality using Redis as a persistent storage backend.
Supports both global rate limiting and specific endpoint rate limiting with
configurable windows and limits.
"""

import logging
import time
import uuid
from typing import Dict, Optional, Tuple

from redis.exceptions import RedisError

from redis import Redis

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter implementation using Redis"""

    def __init__(
        self,
        redis_client: Redis,
        default_window: int = 300,  # 5 minutes
        default_max_requests: int = 100,
    ):
        """Initialize rate limiter with Redis client

        Args:
            redis_client: Redis client instance
            default_window: Default time window in seconds
            default_max_requests: Default maximum requests per window
        """
        self.redis = redis_client
        self.default_window = default_window
        self.default_max_requests = default_max_requests

    def _get_key(self, ip: str, endpoint: Optional[str] = None) -> str:
        """Generate Redis key for rate limiting

        Args:
            ip: IP address
            endpoint: Optional endpoint name for specific limiting

        Returns:
            Redis key string
        """
        base_key = f"rate_limit:{ip}"
        return f"{base_key}:{endpoint}" if endpoint else base_key

    def check_rate_limit(
        self,
        ip: str,
        endpoint: Optional[str] = None,
        window: Optional[int] = None,
        max_requests: Optional[int] = None,
    ) -> Tuple[bool, int, Dict[str, str]]:
        """Check if IP has exceeded rate limit

        Args:
            ip: IP address to check
            endpoint: Optional endpoint name for specific limiting
            window: Optional custom time window
            max_requests: Optional custom request limit

        Returns:
            Tuple of (allowed: bool, wait_time: int, headers: dict)
            Headers contain standard rate limit information:
            - X-RateLimit-Limit: Maximum requests allowed
            - X-RateLimit-Remaining: Requests remaining in window
            - X-RateLimit-Reset: Time in seconds until window resets
        """
        window = window or self.default_window
        max_requests = max_requests or self.default_max_requests
        key = self._get_key(ip, endpoint)
        now = int(time.time())

        try:
            # Clean old entries
            self.redis.zremrangebyscore(key, 0, now - window)

            # Add new request first
            unique_member = f"{now}_{uuid.uuid4()}"
            pipe = self.redis.pipeline()
            pipe.zadd(key, {unique_member: now})
            pipe.expire(key, window)
            pipe.zcard(key)  # Get updated count
            results = pipe.execute()
            current_count = results[-1]  # Last result is zcard

            logger.info(
                f"Rate limit check - Key: {key}, Count: {current_count}, Max: {max_requests}"
            )

            # Get oldest request timestamp for reset time
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            oldest_time = int(oldest[0][1]) if oldest else now
            reset_time = max(0, oldest_time + window - now)

            # Prepare rate limit headers
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(max(0, max_requests - current_count)),
                "X-RateLimit-Reset": str(reset_time),
            }

            # Check if we've exceeded the limit
            if current_count > max_requests:
                # Remove the request we just added since it was rejected
                self.redis.zrem(key, unique_member)

                logger.info(f"Rate limit exceeded - Key: {key}, Wait time: {reset_time}s")
                return False, reset_time, headers

            logger.info(f"Request allowed - Key: {key}")
            return True, 0, headers

        except RedisError as e:
            logger.error(f"Redis error in rate limiting: {e}")
            # Fail open to allow requests if Redis is down
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "N/A",
                "X-RateLimit-Reset": "N/A",
            }
            return True, 0, headers

    def record_failed_login(
        self, ip: str, window: Optional[int] = None, max_attempts: Optional[int] = None
    ) -> Tuple[bool, int, Dict[str, str]]:
        """Record a failed login attempt and check if IP should be blocked

        Args:
            ip: IP address to check
            window: Optional custom time window
            max_attempts: Optional custom attempt limit

        Returns:
            Tuple of (allowed: bool, wait_time: int, headers: dict)
        """
        return self.check_rate_limit(
            ip, endpoint="login_attempts", window=window, max_requests=max_attempts
        )

    def reset_for_tests(self):
        """Reset all rate limits for testing purposes"""
        try:
            # Delete all rate limit keys
            pattern = "rate_limit:*"
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info("Reset all rate limits for testing")
        except RedisError as e:
            logger.error(f"Redis error in reset_for_tests: {e}")
