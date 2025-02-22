"""
Sentry middleware for request processing and context enrichment.
"""

import time
from typing import Any, Awaitable, Callable

import sentry_sdk
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog.contextvars import bind_contextvars

from server.core.config import get_settings
from server.core.monitoring import monitor
from server.core.sentry import set_transaction_name, set_user_context

logger = structlog.get_logger(__name__)


class SentryMiddleware(BaseHTTPMiddleware):
    """Middleware for enriching Sentry context with request information."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process each request and add context to Sentry."""
        settings = get_settings()
        start_time = time.time()
        had_error = False

        # Set transaction name based on route
        transaction_name = f"{request.method} {request.url.path}"
        set_transaction_name(transaction_name)

        # Add request context
        bind_contextvars(
            http_method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Get user from request if available
        if hasattr(request.state, "user"):
            user = request.state.user
            set_user_context(
                user_id=str(user.id),
                email=user.email,
                username=user.username,
                custom_data={
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "roles": user.roles if hasattr(user, "roles") else None,
                },
            )

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000

            # Add response context
            bind_contextvars(
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                duration_ms=duration_ms,
            )

            # Record request metrics
            had_error = response.status_code >= 500
            monitor.record_request(duration_ms, had_error=had_error)

            # Update sampling rates based on current metrics
            current_rates = monitor.get_current_sample_rates()
            sentry_sdk.set_sampling_rate("traces", current_rates["traces"])

            # Add performance metrics if enabled
            if settings.SENTRY_TRACES_SAMPLE_RATE > 0:
                sentry_sdk.set_measurement("response_time_ms", duration_ms, unit="millisecond")

            return response

        except Exception as e:
            # Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            monitor.record_request(duration_ms, had_error=True)

            # Ensure we capture the error with full context
            logger.exception("Request processing failed", exc_info=e)
            raise
