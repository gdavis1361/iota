"""Rate limiter implementation with Redis backend."""
import time
from typing import Dict, Tuple, Optional
import redis
from redis.exceptions import RedisError

from server.core.config import RateLimitConfig

class RateLimiter:
    """Rate limiter with Redis-based storage and flexible limits."""
    
    def __init__(self, config: RateLimitConfig, redis_client: Optional[redis.Redis] = None):
        """Initialize rate limiter with configuration.
        
        Args:
            config: Rate limiting configuration
            redis_client: Optional Redis client for testing
        """
        self.config = config
        
        # Initialize Redis connection if not provided
        if redis_client is None:
            self.redis = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                decode_responses=True
            )
        else:
            self.redis = redis_client
            
        # Verify Redis connection
        try:
            self.redis.ping()
        except RedisError as e:
            raise RedisError(f"Failed to connect to Redis: {e}")
    
    def _get_key(self, identifier: str, endpoint: Optional[str] = None) -> str:
        """Generate Redis key for rate limiting.
        
        Args:
            identifier: Client identifier (e.g. IP)
            endpoint: Optional endpoint for endpoint-specific limits
            
        Returns:
            Redis key string
        """
        base_key = f"rate_limit:{identifier}"
        if endpoint:
            return f"{base_key}:{endpoint}"
        return base_key
    
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
                window = self.config.endpoint_limits[endpoint]["window"]
                max_requests = self.config.endpoint_limits[endpoint]["max_requests"]
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
            reset_time = int(time.time()) + ttl
            
            # Prepare headers
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time)
            }
            
            # Check if rate limit exceeded
            if current > max_requests:
                headers["Retry-After"] = str(ttl)
                return False, ttl, headers
                
            return True, 0, headers
            
        except RedisError:
            # If Redis fails, fail open but return no headers
            return True, 0, {}
    
    def reset_limit(self, identifier: str, endpoint: Optional[str] = None) -> None:
        """Reset rate limit for identifier.
        
        Args:
            identifier: Client identifier to reset
            endpoint: Optional endpoint-specific limit to reset
        """
        try:
            key = self._get_key(identifier, endpoint)
            self.redis.delete(key)
        except RedisError:
            # Ignore Redis errors on reset
            pass
