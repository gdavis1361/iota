"""Rate Limiting Implementation

This module provides a Redis-based rate limiting implementation that:
1. Uses centralized configuration
2. Supports endpoint-specific limits
3. Includes comprehensive monitoring
4. Provides detailed error handling
"""

import time
import logging
from typing import Tuple, Optional, Dict, Any
from redis import Redis
from redis.exceptions import RedisError

from server.core.config import RateLimitConfig
from server.core.config.validation import ConfigurationMetrics

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter with configuration integration."""
    
    def __init__(self, config: RateLimitConfig, redis_client: Optional[Redis] = None):
        """Initialize rate limiter with configuration.
        
        Args:
            config: Rate limiting configuration
            redis_client: Optional Redis client (will create if not provided)
        """
        self.config = config
        self.metrics = ConfigurationMetrics.get_instance()
        
        # Initialize Redis client if not provided
        self.redis = redis_client or Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            decode_responses=True
        )
        
        # Validate Redis connection
        try:
            self.redis.ping()
        except RedisError as e:
            logger.error(f"Redis connection failed: {e}")
            self.metrics.record_error("Redis connection failed", "rate_limiter")
            raise
    
    def _get_key(self, ip: str, endpoint: Optional[str] = None) -> str:
        """Generate Redis key for rate limiting.
        
        Args:
            ip: Client IP address
            endpoint: Optional endpoint path
            
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
        max_requests: Optional[int] = None
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """Check if request is within rate limits.
        
        Args:
            ip: Client IP address
            endpoint: Optional endpoint path
            window: Optional override for time window
            max_requests: Optional override for max requests
            
        Returns:
            Tuple of (allowed: bool, wait_time: int, headers: Dict[str, Any])
        """
        start_time = time.time()
        
        try:
            # Get limits from config if not overridden
            if endpoint and not (window and max_requests):
                limits = self.config.get_endpoint_limits(endpoint)
                window = window or limits["window"]
                max_requests = max_requests or limits["max_requests"]
            else:
                window = window or self.config.default_window
                max_requests = max_requests or self.config.default_max_requests
            
            # Get current count
            key = self._get_key(ip, endpoint)
            current = int(self.redis.get(key) or 0)
            ttl = self.redis.ttl(key)
            
            # Calculate remaining time and requests
            if ttl < 0:
                # Key doesn't exist or has expired
                self.redis.setex(key, window, 1)
                current = 1
                ttl = window
            
            allowed = current <= max_requests
            wait_time = ttl if not allowed else 0
            
            # Increment counter if allowed
            if allowed:
                self.redis.incr(key)
            
            # Prepare headers
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(max(0, max_requests - current)),
                "X-RateLimit-Reset": str(int(time.time() + ttl))
            }
            
            if not allowed:
                headers["Retry-After"] = str(wait_time)
            
            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_validation(duration_ms)
            
            return allowed, wait_time, headers
            
        except RedisError as e:
            logger.error(f"Rate limit check failed: {e}")
            self.metrics.record_error(str(e), "rate_limiter")
            # Fail open to prevent blocking all traffic
            return True, 0, {}
