"""Error handlers for FastAPI application."""
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom API error."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def create_error_response(
    status_code: int,
    detail: str,
    error_code: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create standardized error response."""
    response = {
        "detail": detail,
        "status_code": status_code,
    }
    if error_code:
        response["error_code"] = error_code
    if correlation_id:
        response["correlation_id"] = correlation_id
    return response


def get_request_info(request: Request) -> Dict[str, Any]:
    """Get standardized request information for logging."""
    return {
        "url": str(request.url),
        "path": request.url.path,
        "method": request.method,
        "client_host": request.client.host if request.client else None,
        "correlation_id": str(uuid.uuid4()),
    }


async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors."""
    request_info = get_request_info(request)
    logger.error(
        "api_error",
        extra={
            **request_info,
            "error_message": exc.message,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            status_code=exc.status_code,
            detail=exc.message,
            error_code=exc.error_code,
            correlation_id=request_info["correlation_id"],
        ),
    )


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity errors."""
    request_info = get_request_info(request)
    error_str = str(exc).lower()  # Case-insensitive comparison

    if "duplicate" in error_str and "email" in error_str:
        detail = "Email already registered"
        error_code = "DUPLICATE_EMAIL"
    else:
        detail = "Resource already exists"
        error_code = "DUPLICATE_RESOURCE"

    logger.warning(
        "integrity_error",
        extra={
            **request_info,
            "error": error_str,
            "error_type": type(exc).__name__,
            "error_code": error_code,
            "status_code": status.HTTP_409_CONFLICT,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code,
            correlation_id=request_info["correlation_id"],
        ),
    )


async def handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled errors."""
    request_info = get_request_info(request)

    # Get error details
    error_detail = str(exc) if settings.DEBUG else "Internal server error"
    error_type = type(exc).__name__

    # Log the error with full context
    logger.error(
        "unhandled_error",
        extra={
            **request_info,
            "error": str(exc),
            "error_type": error_type,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        exc_info=True,  # Include stack trace in logs
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
            error_code="INTERNAL_ERROR",
            correlation_id=request_info["correlation_id"],
        ),
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle all errors globally."""
        try:
            return await call_next(request)
        except APIError as exc:
            return await handle_api_error(request, exc)
        except IntegrityError as exc:
            return await handle_integrity_error(request, exc)
        except Exception as exc:
            return await handle_unhandled_error(request, exc)


def setup_error_handlers(app: FastAPI) -> None:
    """Set up error handlers for FastAPI application."""
    logger.info("registering_error_handlers")

    # Add error handling middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # Also register exception handlers as a backup
    app.add_exception_handler(APIError, handle_api_error)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(Exception, handle_unhandled_error)

    logger.info("registered_error_handlers")
