#!/usr/bin/env python3
"""Tests for the IOTA Performance Monitoring Dashboard

This module contains comprehensive tests for the web dashboard's security features,
including authentication, rate limiting, user management, and audit logging.
"""

import json
import os
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from web_dashboard import (
    MAX_LOGIN_ATTEMPTS,
    USERS,
    app,
    audit_log,
    check_login_attempts,
    check_password_strength,
    check_rate_limit,
    load_users,
)
from werkzeug.security import generate_password_hash


class TestWebDashboardSecurity(unittest.TestCase):
    """Test suite for web dashboard security features"""

    def setUp(self):
        """Set up test environment"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
        self.client = app.test_client()

        # Create test user data
        self.test_users = {
            "admin": {
                "password": generate_password_hash("admin123!@#", method="pbkdf2:sha256"),
                "role": "admin",
            },
            "user1": {
                "password": generate_password_hash("user123!@#", method="pbkdf2:sha256"),
                "role": "user",
            },
        }

        # Mock users file
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                self.test_users
            )
            global USERS
            USERS = load_users()

        # Reset rate limit counters
        from web_dashboard import failed_logins, request_counts

        request_counts.clear()
        failed_logins.clear()

    def tearDown(self):
        """Clean up after each test"""
        # Reset rate limit counters
        from web_dashboard import failed_logins, request_counts

        request_counts.clear()
        failed_logins.clear()

    def test_password_strength(self):
        """Test password strength validation"""
        # Test valid password
        valid, _ = check_password_strength("StrongP@ss123")
        self.assertTrue(valid)

        # Test password too short
        valid, msg = check_password_strength("Weak1!")
        self.assertFalse(valid)
        self.assertIn("12 characters", msg)

        # Test missing uppercase
        valid, msg = check_password_strength("weakpassword123!")
        self.assertFalse(valid)
        self.assertIn("uppercase", msg)

        # Test missing lowercase
        valid, msg = check_password_strength("STRONGPASSWORD123!")
        self.assertFalse(valid)
        self.assertIn("lowercase", msg)

        # Test missing numbers
        valid, msg = check_password_strength("StrongPassword!@#")
        self.assertFalse(valid)
        self.assertIn("numbers", msg)

        # Test missing special characters
        valid, msg = check_password_strength("StrongPassword123")
        self.assertFalse(valid)
        self.assertIn("special characters", msg)

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        test_ip = "127.0.0.1"

        # Test within limits
        for _ in range(99):  # Just under limit
            allowed, _ = check_rate_limit(test_ip)
            self.assertTrue(allowed)

        # Test exceeding limits
        for _ in range(10):  # Go over limit
            allowed, wait_time = check_rate_limit(test_ip)
            if not allowed:
                self.assertTrue(wait_time > 0)
                break
        else:
            self.fail("Rate limit not enforced")

    def test_login_attempts(self):
        """Test login attempt limiting"""
        test_ip = "127.0.0.1"

        # Record failed attempts
        for _ in range(MAX_LOGIN_ATTEMPTS):
            self.client.post("/login", data={"username": "admin", "password": "wrongpass"})

        # Test that next attempt is blocked
        response = self.client.post("/login", data={"username": "admin", "password": "wrongpass"})
        self.assertIn(b"Too many failed attempts", response.data)

    @patch("logging.Logger.info")
    def test_audit_logging(self, mock_log):
        """Test audit logging functionality"""
        event_type = "TEST_EVENT"
        username = "test_user"
        ip = "127.0.0.1"
        details = "Test event details"
        success = True

        audit_log(event_type, username, ip, details, success)

        # Verify log format
        mock_log.assert_called_once()
        log_msg = mock_log.call_args[0][0]
        self.assertIn("AUDIT", log_msg)
        self.assertIn(event_type, log_msg)
        self.assertIn(username, log_msg)
        self.assertIn(ip, log_msg)
        self.assertIn(details, log_msg)
        self.assertIn(str(success), log_msg)

    def test_login_endpoint(self):
        """Test login endpoint with rate limiting"""
        # Test successful login
        with patch("web_dashboard.USERS", self.test_users):
            response = self.client.post(
                "/login",
                data={"username": "admin", "password": "admin123!@#"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)  # Should reach index page

            # Test failed login
            response = self.client.post(
                "/login", data={"username": "admin", "password": "wrongpass"}
            )
            self.assertEqual(response.status_code, 200)  # Stay on login page
            self.assertIn(b"Invalid credentials", response.data)

    def test_user_management(self):
        """Test user management endpoints"""
        # Login as admin
        with patch("web_dashboard.USERS", self.test_users):
            # First establish a session
            with self.client.session_transaction() as sess:
                sess["username"] = "admin"
                sess["csrf_token"] = "test_token"

            # Test user listing with CSRF token
            response = self.client.get("/api/users", headers={"X-CSRF-Token": "test_token"})
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn("admin", data)
            self.assertIn("user1", data)

            # Test user deletion with CSRF token
            response = self.client.delete(
                "/api/users?username=admin", headers={"X-CSRF-Token": "test_token"}
            )
            self.assertEqual(response.status_code, 400)  # Can't delete admin

            response = self.client.delete(
                "/api/users?username=nonexistent", headers={"X-CSRF-Token": "test_token"}
            )
            self.assertEqual(response.status_code, 404)  # User not found


if __name__ == "__main__":
    unittest.main()
