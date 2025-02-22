"""Rate limiter implementation.

This module provides a Redis-backed rate limiter with support for:
- Global default rate limits
- Endpoint-specific rate limits
- Configurable time windows
- Rate limit headers
- Graceful Redis failure handling

Example:
    ```python
    from redis import Redis
    from server.core.config import create_settings

    settings = create_settings()
    redis = Redis(host='localhost', port=6379)

    limiter = RateLimiter(settings.rate_limit_config, redis)
    allowed, wait_time, headers = limiter.check_rate_limit('127.0.0.1')

    if not allowed:
        return {'error': 'Rate limited'}, 429, headers
    ```

Rate Limit Headers:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Remaining requests in window
    - X-RateLimit-Reset: Seconds until window reset
    - Retry-After: Present when rate limited

Configuration:
    Rate limits are configured through RateLimitConfig:
    ```python
    RateLimitConfig(
        default_window=60,  # Default time window in seconds
        default_max_requests=100,  # Default max requests per window
        endpoint_limits={  # Optional endpoint-specific limits
            "/api/endpoint": EndpointLimit(
                window=30,
                max_requests=50
            )
        }
    )
"""

from typing import Dict, Optional, Tuple

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode
from redis.exceptions import RedisError

from redis import Redis
from server.core.config import RateLimitConfig

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create metrics
rate_limit_counter = meter.create_counter(
    "rate_limit_requests", description="Number of rate limit checks", unit="1"
)

rate_limit_duration = meter.create_histogram(
    "rate_limit_duration", description="Duration of rate limit checks", unit="s"
)

redis_error_counter = meter.create_counter(
    "redis_errors", description="Number of Redis errors", unit="1"
)


class RateLimiter:
    """Rate limiter using Redis.

    This class provides rate limiting functionality with:
    - Redis-based storage for distributed rate limiting
    - Support for global and endpoint-specific limits
    - Configurable time windows and request limits
    - Comprehensive rate limit headers
    - Graceful failure handling

    The rate limiter uses Redis sorted sets to track requests
    and automatically handles cleanup of expired entries.

    Attributes:
        config: Rate limit configuration
        redis: Redis client instance
    """

    def __init__(self, config: RateLimitConfig, redis_client: Redis):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration
            redis_client: Redis client instance

        Raises:
            RedisError: If Redis connection fails
        """
        self.config = config
        self.redis = redis_client

        # Test Redis connection
        try:
            with tracer.start_as_current_span("redis_ping") as span:
                self.redis.ping()
                span.set_status(Status(StatusCode.OK))
        except RedisError as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            redis_error_counter.add(1)
            raise RedisError(f"Failed to connect to Redis: {e}")

    def _get_key(self, identifier: str, endpoint: Optional[str] = None) -> str:
        """Get Redis key for rate limit counter.

        Args:
            identifier: Client identifier
            endpoint: Optional endpoint name

        Returns:
            Redis key string in format:
            - rate_limit:{identifier} for global limits
            - rate_limit:{identifier}:{endpoint} for endpoint limits
        """
        base = f"rate_limit:{identifier}"
        if endpoint:
            return f"{base}:{endpoint}"
        return base

    def check_rate_limit(
        self, identifier: str, endpoint: Optional[str] = None
    ) -> Tuple[bool, int, Dict[str, str]]:
        """Check if request is allowed under rate limit.

        This method:
        1. Gets appropriate limits (endpoint-specific or default)
        2. Checks and updates request count
        3. Returns allow/deny decision with headers

        Args:
            identifier: Client identifier (e.g. IP)
            endpoint: Optional endpoint for endpoint-specific limits

        Returns:
            Tuple of:
            - bool: Whether request is allowed
            - int: Seconds to wait if rate limited
            - dict: Rate limit headers

        Headers:
            - X-RateLimit-Limit: Maximum requests allowed
            - X-RateLimit-Remaining: Remaining requests in window
            - X-RateLimit-Reset: Seconds until window reset
            - Retry-After: Present when rate limited

        Note:
            On Redis errors, requests are allowed (fail open) with
            empty headers to prevent service disruption.
        """
        with tracer.start_as_current_span("check_rate_limit") as span:
            span.set_attribute("identifier", identifier)
            if endpoint:
                span.set_attribute("endpoint", endpoint)

            try:
                # Get appropriate limits
                if endpoint and endpoint in self.config.endpoint_limits:
                    limit = self.config.endpoint_limits[endpoint]
                    window = limit.window
                    max_requests = limit.max_requests
                else:
                    window = self.config.default_window
                    max_requests = self.config.default_max_requests

                span.set_attribute("window", window)
                span.set_attribute("max_requests", max_requests)

                # Get current count and TTL
                key = self._get_key(identifier, endpoint)
                with tracer.start_as_current_span("redis_operations") as redis_span:
                    current = int(self.redis.get(key) or 0)
                    ttl = self.redis.ttl(key)

                    # If key doesn't exist, initialize it
                    if ttl == -2:  # Key doesn't exist
                        self.redis.setex(key, window, 1)
                        current = 1
                        ttl = window
                    else:
                        # Increment counter
                        current = self.redis.incr(key)

                    redis_span.set_attribute("current_count", current)
                    redis_span.set_attribute("ttl", ttl)

                # Calculate remaining requests and reset time
                remaining = max(0, max_requests - current)
                reset = max(0, ttl)

                # Build response headers
                headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset),
                }

                # Check if rate limited
                is_limited = current > max_requests
                if is_limited:
                    headers["Retry-After"] = str(reset)
                    span.set_attribute("rate_limited", True)
                else:
                    span.set_attribute("rate_limited", False)

                # Record metrics
                rate_limit_counter.add(1, {"limited": str(is_limited)})

                span.set_status(Status(StatusCode.OK))
                return not is_limited, reset, headers

            except RedisError as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                redis_error_counter.add(1)
                # Redis error - fail open
                return True, 0, {}
