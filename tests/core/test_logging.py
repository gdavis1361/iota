"""
Unit tests for the logging module.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import structlog

from server.core.config import Settings
from server.core.logging import correlation_id_context, get_correlation_id, logger, setup_logging


@pytest.fixture
def temp_log_file(tmp_path):
    return tmp_path / "test.log"


@pytest.fixture
def test_settings(temp_log_file):
    return Settings(LOG_LEVEL="DEBUG", LOG_FORMAT="json", LOG_FILE_PATH=str(temp_log_file))


def test_correlation_id_generation():
    """Test correlation ID generation and context."""
    # Test default correlation ID
    assert get_correlation_id() != ""

    # Test correlation ID context
    test_id = "test-correlation-id"
    with correlation_id_context(test_id):
        assert get_correlation_id() == test_id

    # Test nested contexts
    outer_id = "outer-id"
    inner_id = "inner-id"
    with correlation_id_context(outer_id):
        assert get_correlation_id() == outer_id
        with correlation_id_context(inner_id):
            assert get_correlation_id() == inner_id
        assert get_correlation_id() == outer_id


def test_json_logging(test_settings, temp_log_file):
    """Test JSON structured logging format."""
    with patch("server.core.logging.get_settings", return_value=test_settings):
        setup_logging()

        test_message = "test log message"
        test_data = {"key": "value"}

        # Log a test message
        logger.info(test_message, **test_data)

        # Read and parse the log file
        with open(temp_log_file) as f:
            log_entry = json.loads(f.readline())

        # Verify log structure
        assert log_entry["event"] == test_message
        assert log_entry["key"] == test_data["key"]
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "correlation_id" in log_entry


def test_console_logging(test_settings, capsys):
    """Test console logging format."""
    test_settings.LOG_FORMAT = "console"

    with patch("server.core.logging.get_settings", return_value=test_settings):
        setup_logging()

        test_message = "test console log"
        logger.info(test_message)

        captured = capsys.readouterr()
        assert test_message in captured.out


def test_log_levels(test_settings):
    """Test different log levels."""
    with patch("server.core.logging.get_settings", return_value=test_settings):
        setup_logging()

        # Create a mock handler
        mock_handler = MagicMock()
        logging.getLogger().addHandler(mock_handler)

        # Test DEBUG level
        logger.debug("debug message")
        assert mock_handler.handle.called

        # Test INFO level
        mock_handler.reset_mock()
        logger.info("info message")
        assert mock_handler.handle.called

        # Test ERROR level
        mock_handler.reset_mock()
        logger.error("error message")
        assert mock_handler.handle.called


def test_sensitive_data_masking(test_settings, temp_log_file):
    """Test masking of sensitive data in logs."""
    with patch("server.core.logging.get_settings", return_value=test_settings):
        setup_logging()

        sensitive_data = "secret123"
        masked_message = "password: " + sensitive_data

        logger.info("user_login", password=sensitive_data)

        with open(temp_log_file) as f:
            log_entry = json.loads(f.readline())

        # Verify sensitive data is not in log
        assert sensitive_data not in str(log_entry)
        assert "password" in log_entry  # Key should exist
        assert log_entry["password"] != sensitive_data  # But value should be masked


def test_exception_logging(test_settings, temp_log_file):
    """Test exception logging and formatting."""
    with patch("server.core.logging.get_settings", return_value=test_settings):
        setup_logging()

        try:
            raise ValueError("test exception")
        except Exception as e:
            logger.exception("caught error")

        with open(temp_log_file) as f:
            log_entry = json.loads(f.readline())

        assert "exception" in log_entry
        assert "ValueError" in str(log_entry["exception"])
        assert "test exception" in str(log_entry["exception"])
