"""Rate limiter implementation."""
from typing import Dict, Optional, Tuple
from redis import Redis
from redis.exceptions import RedisError

from server.core.config import RateLimitConfig

class RateLimiter:
    """Rate limiter using Redis."""

    def __init__(self, config: RateLimitConfig, redis_client: Redis):
        """Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
            redis_client: Redis client instance
        """
        self.config = config
        self.redis = redis_client
        
        # Test Redis connection
        try:
            self.redis.ping()
        except RedisError as e:
            raise RedisError(f"Failed to connect to Redis: {e}")
    
    def _get_key(self, identifier: str, endpoint: Optional[str] = None) -> str:
        """Get Redis key for rate limit counter.
        
        Args:
            identifier: Client identifier
            endpoint: Optional endpoint name
            
        Returns:
            Redis key string
        """
        base = f"rate_limit:{identifier}"
        if endpoint:
            return f"{base}:{endpoint}"
        return base
    
    def check_rate_limit(
        self,
        identifier: str,
        endpoint: Optional[str] = None
    ) -> Tuple[bool, int, Dict[str, str]]:
        """Check if request is allowed under rate limit.
        
        Args:
            identifier: Client identifier (e.g. IP)
            endpoint: Optional endpoint for endpoint-specific limits
            
        Returns:
            Tuple of:
            - bool: Whether request is allowed
            - int: Seconds to wait if rate limited
            - dict: Rate limit headers
        """
        try:
            # Get appropriate limits
            if endpoint and endpoint in self.config.endpoint_limits:
                limit = self.config.endpoint_limits[endpoint]
                window = limit.window
                max_requests = limit.max_requests
            else:
                window = self.config.default_window
                max_requests = self.config.default_max_requests
            
            # Get current count and TTL
            key = self._get_key(identifier, endpoint)
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
            
            # Calculate remaining requests and reset time
            remaining = max(0, max_requests - current)
            reset = max(0, ttl)
            
            # Build response headers
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset)
            }
            
            # Check if rate limited
            if current > max_requests:
                headers["Retry-After"] = str(reset)
                return False, reset, headers
            
            return True, 0, headers
            
        except RedisError:
            # Redis error - fail open
            return True, 0, {}
