#!/usr/bin/env python3
"""Tests for Rate Limiting Module

Tests the Redis-based rate limiting functionality, including global rate limiting
and login attempt tracking.
"""

import time
import unittest

import fakeredis
from rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Test suite for rate limiter functionality"""

    def setUp(self):
        """Set up test environment with fake Redis"""
        self.redis = fakeredis.FakeRedis()
        self.limiter = RateLimiter(
            self.redis,
            default_window=5,  # 5 second window for faster testing
            default_max_requests=5,  # 5 requests per window
        )

    def tearDown(self):
        """Clean up after tests"""
        self.redis.flushall()

    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality"""
        ip = "127.0.0.1"

        # Test successful requests within limit
        for i in range(5):
            allowed, wait_time, headers = self.limiter.check_rate_limit(ip)
            print(f"Request {i+1}: allowed={allowed}, wait_time={wait_time}, headers={headers}")
            self.assertTrue(allowed)
            self.assertEqual(wait_time, 0)
            self.assertEqual(headers["X-RateLimit-Limit"], "5")
            self.assertEqual(headers["X-RateLimit-Remaining"], str(5 - (i + 1)))
            self.assertTrue(int(headers["X-RateLimit-Reset"]) >= 0)

        # Test request exceeding limit
        allowed, wait_time, headers = self.limiter.check_rate_limit(ip)
        print(f"Excess request: allowed={allowed}, wait_time={wait_time}, headers={headers}")
        self.assertFalse(allowed)
        self.assertTrue(wait_time > 0)
        self.assertEqual(headers["X-RateLimit-Limit"], "5")
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")
        self.assertTrue(int(headers["X-RateLimit-Reset"]) > 0)

        # Wait for window to expire
        time.sleep(5)

        # Test requests are allowed again
        allowed, wait_time, headers = self.limiter.check_rate_limit(ip)
        print(f"After window: allowed={allowed}, wait_time={wait_time}, headers={headers}")
        self.assertTrue(allowed)
        self.assertEqual(wait_time, 0)
        self.assertEqual(headers["X-RateLimit-Remaining"], "4")

    def test_endpoint_specific_limiting(self):
        """Test rate limiting for specific endpoints"""
        ip = "127.0.0.1"

        # Test endpoint-specific limits
        for i in range(3):
            allowed, wait_time, headers = self.limiter.check_rate_limit(
                ip, endpoint="api", max_requests=3
            )
            self.assertTrue(allowed)
            self.assertEqual(wait_time, 0)
            self.assertEqual(headers["X-RateLimit-Limit"], "3")
            self.assertEqual(headers["X-RateLimit-Remaining"], str(3 - (i + 1)))

        # Should be blocked for this endpoint
        allowed, wait_time, headers = self.limiter.check_rate_limit(
            ip, endpoint="api", max_requests=3
        )
        self.assertFalse(allowed)
        self.assertTrue(wait_time > 0)
        self.assertEqual(headers["X-RateLimit-Limit"], "3")
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")

        # But still allowed for other endpoints
        allowed, wait_time, headers = self.limiter.check_rate_limit(ip)
        self.assertTrue(allowed)
        self.assertEqual(wait_time, 0)
        self.assertEqual(headers["X-RateLimit-Limit"], "5")
        self.assertTrue(int(headers["X-RateLimit-Remaining"]) >= 0)

    def test_failed_login_tracking(self):
        """Test failed login attempt tracking"""
        ip = "127.0.0.1"

        # Test successful attempts within limit
        for i in range(5):
            allowed, wait_time, headers = self.limiter.record_failed_login(
                ip, window=5, max_attempts=5  # 5 second window for testing
            )
            self.assertTrue(allowed)
            self.assertEqual(wait_time, 0)
            self.assertEqual(headers["X-RateLimit-Limit"], "5")
            self.assertEqual(headers["X-RateLimit-Remaining"], str(5 - (i + 1)))

        # Test exceeding limit
        allowed, wait_time, headers = self.limiter.record_failed_login(ip, window=5, max_attempts=5)
        self.assertFalse(allowed)
        self.assertTrue(wait_time > 0)
        self.assertEqual(headers["X-RateLimit-Limit"], "5")
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")
        self.assertTrue(int(headers["X-RateLimit-Reset"]) > 0)

    def test_test_reset(self):
        """Test resetting rate limits for testing"""
        ip = "127.0.0.1"

        # Add some requests
        for endpoint in [None, "api", "login_attempts"]:
            for _ in range(3):
                allowed, _, headers = self.limiter.check_rate_limit(ip, endpoint=endpoint)
                self.assertTrue(allowed)
                self.assertTrue(int(headers["X-RateLimit-Remaining"]) >= 0)

        # Reset all rate limits
        self.limiter.reset_for_tests()

        # Should be allowed again
        for endpoint in [None, "api", "login_attempts"]:
            allowed, wait_time, headers = self.limiter.check_rate_limit(ip, endpoint=endpoint)
            self.assertTrue(allowed)
            self.assertEqual(wait_time, 0)
            self.assertEqual(headers["X-RateLimit-Remaining"], "4")


if __name__ == "__main__":
    unittest.main()
