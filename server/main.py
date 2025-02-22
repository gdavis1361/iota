import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Info, make_asgi_app

from app.core.config import settings

# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total number of HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["method", "endpoint"]
)

TEST_EXECUTION_DURATION = Histogram(
    "test_execution_duration_seconds", "Test execution duration in seconds", ["test_name"]
)

SERVER_INFO = Info("iota_server", "Information about the IOTA server")
SERVER_INFO.info({"version": settings.VERSION, "project_name": settings.PROJECT_NAME})

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="JSquared API Server",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()

    # Use context manager for histogram
    with REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).time():
        response = await call_next(request)

    # Record request count
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time(), "version": settings.VERSION}


# Test endpoints
@app.get("/api/v1/data")
async def get_data(request: Request):
    """Test endpoint for data retrieval."""
    with TEST_EXECUTION_DURATION.labels(test_name="get_data").time():
        try:
            return {"message": "Data retrieved successfully", "timestamp": time.time()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/data")
async def create_data(request: Request):
    """Test endpoint for data creation."""
    with TEST_EXECUTION_DURATION.labels(test_name="create_data").time():
        try:
            return JSONResponse(content={"message": "Data created successfully"}, status_code=201)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Root endpoint
@app.get("/")
async def root():
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/api/docs",
        "health_check": "/api/health",
    }


# Include routers
# from app.api.v1 import auth, users, common
# app.include_router(auth.router, prefix=settings.API_V1_STR)
# app.include_router(users.router, prefix=settings.API_V1_STR)
# app.include_router(common.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.RELOAD)
