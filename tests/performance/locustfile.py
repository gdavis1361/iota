"""Performance tests for the rate limiter using Locust."""

import time
import uuid
from typing import Dict, Optional

from locust import HttpUser, between, events, task

import redis


class RateLimitUser(HttpUser):
    """Simulates user behavior for rate limit testing."""

    wait_time = between(0.1, 1.0)  # Time between requests

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_client: Optional[redis.Redis] = None
        self.test_endpoints = [
            "/api/v1/auth/token",
            "/api/v1/users",
            "/api/v1/data",
            "/api/v1/metrics",
        ]

    def on_start(self):
        """Initialize Redis connection on start."""
        self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

    def on_stop(self):
        """Clean up Redis connection."""
        if self.redis_client:
            self.redis_client.close()

    @task(3)
    def test_normal_endpoints(self):
        """Test regular API endpoints."""
        for endpoint in self.test_endpoints:
            with self.client.get(
                endpoint, headers={"X-Request-ID": str(uuid.uuid4())}, catch_response=True
            ) as response:
                if response.status_code == 429:  # Rate limited
                    response.success()  # Expected behavior
                elif response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def test_auth_endpoint(self):
        """Test authentication endpoint with higher rate limit."""
        with self.client.post(
            "/api/v1/auth/token",
            json={"username": "test", "password": "test"},
            headers={"X-Request-ID": str(uuid.uuid4())},
            catch_response=True,
        ) as response:
            if response.status_code == 429:  # Rate limited
                response.success()  # Expected behavior
            elif response.status_code in [200, 401]:  # Success or auth failure
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(2)
    def test_rapid_requests(self):
        """Test rapid request sequences."""
        endpoint = "/api/v1/data"
        results = []

        # Send 10 requests rapidly
        for _ in range(10):
            with self.client.get(
                endpoint, headers={"X-Request-ID": str(uuid.uuid4())}, catch_response=True
            ) as response:
                results.append(response.status_code)
                if response.status_code not in [200, 429]:
                    response.failure(f"Unexpected status code: {response.status_code}")
                else:
                    response.success()

        # Check rate limiting behavior
        rate_limited = results.count(429)
        if rate_limited == 0:
            events.request.fire(
                request_type="rate_limit",
                name="no_rate_limit",
                response_time=0,
                response_length=0,
                exception=Exception("No rate limiting observed"),
            )

    def get_remaining_requests(self, endpoint: str) -> Dict:
        """Get remaining requests for an endpoint."""
        key = f"rate_limit:{endpoint}"
        now = int(time.time())
        count = self.redis_client.zcount(key, now - 3600, now)
        return {"count": count, "remaining": 100 - count}  # Assuming default limit of 100


@events.test_start.add_listener
def on_test_start(**kwargs):
    """Initialize test environment."""
    print("Performance test starting")


@events.test_stop.add_listener
def on_test_stop(**kwargs):
    """Clean up test environment."""
    print("Performance test complete")
