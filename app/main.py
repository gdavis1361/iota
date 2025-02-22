"""Main FastAPI application."""
import structlog
from fastapi import FastAPI, HTTPException, Request, status
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db_verify import check_database_tables, verify_database_connection
from app.core.error_handlers import setup_error_handlers
from app.core.logging import get_route_info, setup_logging
from app.db.session import get_db

# Configure structured logging
setup_logging()
logger = structlog.get_logger()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0",
    redirect_slashes=False,
)

# Set up error handlers
setup_error_handlers(app)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their resolved paths."""
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    response = await call_next(request)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


# Import and include API routers
from app.api.v1.api import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    """Verify configuration and log all registered routes on startup."""
    # Verify database connection
    await verify_database_connection()

    # Get a database session
    async for session in get_db():
        # Check database tables
        await check_database_tables(session)
        break

    # Log all registered routes
    routes = []
    for route in app.routes:
        routes.append(get_route_info(route))

    logger.info(
        "application_startup",
        routes=routes,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )
