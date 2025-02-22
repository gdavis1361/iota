#!/usr/bin/env python3
"""Test server for IOTA rate limiter performance testing."""
import json
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Info

import redis

# Define metrics
TEST_EXECUTION_COUNT = Counter(
    "test_executions_total", "Total number of test executions", ["test_name", "status"]
)

TEST_EXECUTION_DURATION = Histogram(
    "test_execution_duration_seconds", "Test execution duration in seconds", ["test_name"]
)

TEST_ERROR_COUNT = Counter(
    "test_errors_total", "Total number of test errors", ["test_name", "error_type"]
)

TEST_SERVER_INFO = Info("test_server", "Information about the test server")
TEST_SERVER_INFO.info({"version": "1.0.0", "description": "IOTA Rate Limiter Test Server"})

app = FastAPI(title="IOTA Rate Limiter Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        TEST_EXECUTION_COUNT.labels(test_name="health_check", status="success").inc()
        return {"status": "healthy", "redis": "connected"}
    except Exception:
        TEST_EXECUTION_COUNT.labels(test_name="health_check", status="error").inc()
        TEST_ERROR_COUNT.labels(test_name="health_check", error_type="redis_connection").inc()
        return Response(
            content=json.dumps({"status": "unhealthy", "redis": "disconnected"}),
            status_code=503,
            media_type="application/json",
        )


@app.get("/api/v1/data")
async def get_data(request: Request):
    """Test endpoint for data retrieval."""
    with TEST_EXECUTION_DURATION.labels(test_name="get_data").time():
        try:
            TEST_EXECUTION_COUNT.labels(test_name="get_data", status="success").inc()
            return {"message": "Data retrieved successfully", "timestamp": time.time()}
        except Exception:
            TEST_EXECUTION_COUNT.labels(test_name="get_data", status="error").inc()
            TEST_ERROR_COUNT.labels(test_name="get_data", error_type="unknown").inc()
            raise


@app.post("/api/v1/data/create")
async def create_data(request: Request):
    """Test endpoint for data creation."""
    with TEST_EXECUTION_DURATION.labels(test_name="create_data").time():
        try:
            TEST_EXECUTION_COUNT.labels(test_name="create_data", status="success").inc()
            return Response(
                content='{"message": "Data created successfully"}',
                media_type="application/json",
            )
        except Exception:
            TEST_EXECUTION_COUNT.labels(test_name="create_data", status="error").inc()
            TEST_ERROR_COUNT.labels(test_name="create_data", error_type="unknown").inc()
            raise


@app.get("/api/v1/metrics")
async def get_metrics():
    """Test endpoint for metrics retrieval."""
    try:
        total_requests = redis_client.get("total_requests") or "0"
        rate_limited = redis_client.get("rate_limited_requests") or "0"
        return {"total_requests": total_requests, "rate_limited_requests": rate_limited}
    except Exception:
        return {"total_requests": 0, "rate_limited_requests": 0}


@app.get("/api/v1/users")
async def get_users():
    """Test endpoint for user data."""
    return {"total_users": 100, "active_users": 50}


@app.get("/api/v1/auth/token")
async def get_token():
    """Test endpoint for token retrieval."""
    return {"token": "test_token", "expires_in": 3600}


@app.post("/api/v1/auth/token")
async def create_token():
    """Test endpoint for token creation."""
    return {"token": "new_test_token", "expires_in": 3600}


if __name__ == "__main__":
    uvicorn.run("test_server:app", host="0.0.0.0", port=8001, reload=True)
