"""Tests for analyze_config_errors.py script."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.analyze_config_errors import ConfigLogAnalyzer


@pytest.fixture
def sample_logs():
    """Create temporary log files with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create first log file
        log1_path = os.path.join(tmpdir, "config1.log")
        log1_entries = [
            {
                "timestamp": "2025-02-21T09:14:45-05:00",
                "level": "ERROR",
                "message": "Configuration validation error",
                "category": "CONFIG_VALIDATION",
                "extra": {
                    "field": "SENTRY_DSN",
                    "error": "Invalid Sentry DSN format",
                    "source": "sentry_validator",
                },
            },
            {
                "timestamp": "2025-02-21T09:15:30-05:00",
                "level": "CRITICAL",
                "message": "Failed to initialize settings",
                "category": "CONFIG_INIT",
                "extra": {"error": "Missing required fields", "error_type": "ValidationError"},
            },
        ]

        with open(log1_path, "w") as f:
            for entry in log1_entries:
                f.write(json.dumps(entry) + "\n")

        # Create second log file
        log2_path = os.path.join(tmpdir, "config2.log")
        log2_entries = [
            {
                "timestamp": "2025-02-21T09:17:45-05:00",
                "level": "ERROR",
                "message": "Configuration validation error",
                "category": "CONFIG_VALIDATION",
                "extra": {"field": "API_KEY", "error": "Field required", "source": "api_validator"},
            }
        ]

        with open(log2_path, "w") as f:
            for entry in log2_entries:
                f.write(json.dumps(entry) + "\n")

        yield [log1_path, log2_path]


def test_log_loading(sample_logs):
    """Test that logs are loaded correctly."""
    analyzer = ConfigLogAnalyzer(sample_logs)
    analyzer.load_logs()

    assert len(analyzer.errors) == 2  # Only ERROR level entries
    assert len(analyzer.file_errors) == 2  # Two files processed
    assert analyzer.file_errors[sample_logs[0]] == 1  # One error in first file
    assert analyzer.file_errors[sample_logs[1]] == 1  # One error in second file


def test_error_counting(sample_logs):
    """Test error counting functionality."""
    analyzer = ConfigLogAnalyzer(sample_logs)
    analyzer.load_logs()

    assert analyzer.error_counts["Configuration validation error"] == 2
    assert len(analyzer.field_errors) == 2
    assert analyzer.field_errors["SENTRY_DSN"] == 1
    assert analyzer.field_errors["API_KEY"] == 1


def test_date_filtering(sample_logs):
    """Test filtering by date."""
    analyzer = ConfigLogAnalyzer(sample_logs)

    # Test with 1 day filter (should include all)
    analyzer.load_logs(days=1)
    assert len(analyzer.errors) == 2

    # Test with past date (should exclude all)
    analyzer = ConfigLogAnalyzer(sample_logs)
    analyzer.load_logs(days=-1)
    assert len(analyzer.errors) == 0


def test_invalid_json_handling(sample_logs):
    """Test handling of invalid JSON in log files."""
    # Add invalid JSON to first log file
    with open(sample_logs[0], "a") as f:
        f.write("Invalid JSON\n")

    analyzer = ConfigLogAnalyzer(sample_logs)
    analyzer.load_logs()  # Should not raise exception

    # Should still have valid entries
    assert len(analyzer.errors) == 2


def test_missing_file_handling():
    """Test handling of missing log files."""
    analyzer = ConfigLogAnalyzer(["/nonexistent/file.log"])
    analyzer.load_logs()  # Should not raise exception
    assert len(analyzer.errors) == 0


def test_empty_file_handling(sample_logs):
    """Test handling of empty log files."""
    # Create empty log file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        empty_log = f.name

    analyzer = ConfigLogAnalyzer([empty_log])
    analyzer.load_logs()  # Should not raise exception
    assert len(analyzer.errors) == 0

    os.unlink(empty_log)  # Clean up


def test_error_categorization(sample_logs):
    """Test proper categorization of different error types."""
    analyzer = ConfigLogAnalyzer(sample_logs)
    analyzer.load_logs()

    validation_errors = [e for e in analyzer.errors if e.get("category") == "CONFIG_VALIDATION"]
    assert len(validation_errors) == 2

    # Verify error details
    assert any(e.get("extra", {}).get("field") == "SENTRY_DSN" for e in validation_errors)
    assert any(e.get("extra", {}).get("field") == "API_KEY" for e in validation_errors)
