#!/usr/bin/env python3
"""Test server for IOTA rate limiter performance testing."""
import json
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

import redis

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
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return Response(
            content=json.dumps({"status": "unhealthy", "redis": "disconnected"}),
            status_code=503,
            media_type="application/json",
        )


@app.get("/api/v1/data")
async def get_data(request: Request):
    """Test endpoint for data retrieval."""
    return {"message": "Data retrieved successfully", "timestamp": time.time()}


@app.post("/api/v1/data/create")
async def create_data(request: Request):
    """Test endpoint for data creation."""
    return Response(
        content='{"message": "Data created successfully"}',
        status_code=201,
        media_type="application/json",
    )


@app.get("/api/v1/metrics")
async def get_metrics():
    """Test endpoint for metrics retrieval."""
    try:
        total_requests = redis_client.get("total_requests") or "0"
        rate_limited = redis_client.get("rate_limited_requests") or "0"
        return {"total_requests": total_requests, "rate_limited_requests": rate_limited}
    except Exception as e:
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
