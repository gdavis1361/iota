"""Rate limiting middleware with configuration integration."""

import time
from typing import Callable

from app.core.monitoring.rate_limit import RateLimitMetricsMiddleware, RateLimitMonitor
from app.core.rate_limiter import RateLimiter
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from server.core.config import RateLimitConfig


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using centralized configuration."""

    def __init__(self, app: ASGIApp, config: RateLimitConfig):
        """Initialize middleware with configuration.

        Args:
            app: ASGI application
            config: Rate limiting configuration
        """
        super().__init__(app)
        self.config = config
        self.limiter = RateLimiter(config)
        self.monitor = RateLimitMonitor()
        self.metrics_middleware = RateLimitMetricsMiddleware(self.monitor)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            FastAPI response
        """
        # Get client IP and path
        client_ip = request.client.host
        path = request.url.path
        start_time = time.time()

        # Check rate limit using config-based limits
        allowed, wait_time, headers = self.limiter.check_rate_limit(client_ip, endpoint=path)

        # Record metrics
        remaining = int(headers.get("X-RateLimit-Remaining", 0))
        reset_time = int(headers.get("X-RateLimit-Reset", 0))
        self.monitor.record_request(path, client_ip, allowed, remaining, reset_time)

        if not allowed:
            # Record rate limit exceeded
            self.monitor.record_rate_limit_exceeded(
                path, client_ip, wait_time, remaining, reset_time
            )
            return Response(
                content={"error": "Rate limit exceeded", "retry_after": wait_time},
                status_code=429,
                headers=headers,
                media_type="application/json",
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        for header, value in headers.items():
            response.headers[header] = str(value)

        # Track failed login attempts
        if (
            path == "/api/v1/auth/token"
            and response.status_code == 401
            and remaining < self.config.default_max_requests // 2
        ):
            self.monitor.record_failed_login_attempt(client_ip, remaining)

        # Record response time
        self.monitor.record_response_time(path, time.time() - start_time)

        return response
