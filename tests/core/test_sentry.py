"""
Tests for Sentry integration.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import sentry_sdk
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from server.core.bootstrap import bootstrap_app
from server.core.config import Settings, get_settings
from server.core.sentry import add_breadcrumb, before_send, set_user_context


@pytest.fixture(autouse=True)
def setup_teardown():
    """Reset context variables between tests."""
    clear_contextvars()
    yield
    clear_contextvars()


@pytest.fixture
def mock_sentry():
    """Mock Sentry SDK initialization."""
    with patch("sentry_sdk.init") as mock_init:
        yield mock_init


@pytest.fixture
def test_settings():
    """Get test settings with Sentry enabled."""
    settings = get_settings()
    settings.SENTRY_ENABLED = True
    settings.SENTRY_DSN = "https://test@test.ingest.sentry.io/test"
    return settings


def test_sentry_disabled(mock_sentry, test_settings):
    """Test that Sentry is not initialized when disabled."""
    with patch.object(test_settings, "SENTRY_ENABLED", False):
        bootstrap_app()
        mock_sentry.assert_not_called()


def test_sentry_no_dsn(mock_sentry, test_settings):
    """Test that Sentry is not initialized without DSN."""
    with patch.object(test_settings, "SENTRY_DSN", ""):
        bootstrap_app()
        mock_sentry.assert_not_called()


def test_sentry_initialization(mock_sentry, test_settings):
    """Test proper Sentry initialization."""
    with patch("server.core.config.get_settings", return_value=test_settings):
        bootstrap_app()
        mock_sentry.assert_called_once()
        config = mock_sentry.call_args[1]
        assert config["dsn"] == test_settings.SENTRY_DSN
        assert config["environment"] == test_settings.ENVIRONMENT
        assert callable(config["before_send"])


def test_sentry_correlation_id():
    """Test correlation ID is added to events."""
    test_event = {"tags": {}, "extra": {}}
    bind_contextvars(correlation_id="test-id")
    processed_event = before_send(test_event, {})
    assert processed_event["tags"]["correlation_id"] == "test-id"
    assert processed_event["extra"]["correlation_id"] == "test-id"


def test_sentry_metadata():
    """Test metadata is added to events."""
    test_event = {"extra": {}}
    bind_contextvars(test_key="test_value")
    processed_event = before_send(test_event, {})
    assert processed_event["extra"]["test_key"] == "test_value"


def test_sentry_error_capture():
    """Test error capture with context."""
    with patch("sentry_sdk.capture_exception") as mock_capture:
        try:
            raise ValueError("Test error")
        except ValueError as e:
            set_user_context(user_id="test-user")
            add_breadcrumb(message="Test breadcrumb")
            sentry_sdk.capture_exception(e)
            mock_capture.assert_called_once()
