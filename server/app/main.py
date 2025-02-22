import time
import traceback
import uuid
from typing import Any, Dict

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Initialize logging
logger = setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS
logger.loggers["api"].info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    # Log startup configuration
    logger.loggers["api"].info(
        {
            "event": "startup",
            "config": {
                "debug": settings.DEBUG,
                "api_prefix": settings.API_V1_STR,
                "allowed_hosts": settings.ALLOWED_HOSTS,
                "version": settings.VERSION,
            },
        }
    )

    # Initialize database
    try:
        from app.db.session import init_db

        await init_db()
        logger.loggers["db"].info({"event": "database_initialized", "status": "success"})
    except Exception as e:
        logger.loggers["db"].error(
            {
                "event": "database_initialization_failed",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
        )
        raise


@app.on_event("shutdown")
async def shutdown_event():
    # Close database connections
    from app.db.session import close_db

    close_db()

    logger.loggers["api"].info({"event": "shutdown", "message": "Application shutdown completed"})


def log_request_details(
    request: Request, response: Any, duration: float, error: Dict[str, Any] = None
) -> None:
    """Log detailed request information"""
    request_id = str(uuid.uuid4())
    log_data = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "duration": duration,
        "status_code": getattr(response, "status_code", 500),
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent"),
    }

    if error:
        log_data.update(error)
        logger.loggers["api"].error(log_data)
    else:
        logger.loggers["api"].info(log_data)

    return request_id


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    error_detail = None

    try:
        # Add request ID to request state
        request.state.request_id = request_id
        response = await call_next(request)

        # Calculate request duration
        duration = time.time() - start_time

        # Log request metrics
        logger.metrics.record(
            "request_duration_seconds",
            duration,
            {
                "endpoint": request.url.path,
                "method": request.method,
                "status": response.status_code,
            },
        )

        # Track endpoint usage
        logger.metrics.record(
            "endpoint_hits", 1, {"endpoint": request.url.path, "method": request.method}
        )

        # Track rate limiting
        if response.status_code == 429:
            logger.metrics.record(
                "rate_limit_hits",
                1,
                {"endpoint": request.url.path, "ip_range": request.client.host},
            )

        # Track authentication failures
        if response.status_code in (401, 403):
            logger.metrics.record(
                "auth_failures", 1, {"endpoint": request.url.path, "ip_range": request.client.host}
            )

        # Track suspicious patterns
        if response.status_code >= 400:
            logger.metrics.record(
                "suspicious_patterns",
                1,
                {"pattern_type": "error_response", "status_code": response.status_code},
            )

        # Log request details
        log_request_details(request, response, duration)

        return response

    except Exception as e:
        duration = time.time() - start_time
        error_detail = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }

        # Log error details
        log_request_details(request, None, duration, error_detail)

        # Track error metrics
        logger.metrics.record(
            "unhandled_exceptions",
            1,
            {"error_type": type(e).__name__, "endpoint": request.url.path},
        )

        return JSONResponse(
            status_code=500, content={"detail": "Internal server error", "request_id": request_id}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.VERSION, "timestamp": time.time()}


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
    }


def run_server():
    """Run the server using uvicorn"""
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)


if __name__ == "__main__":
    run_server()
