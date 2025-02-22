#!/usr/bin/env python3
"""Unit tests for Redis metrics collection."""
import json
from unittest.mock import MagicMock, mock_open, patch

import pytest
from collect_redis_metrics import collect_metrics, main


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("redis.Redis") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_config():
    """Sample test configuration."""
    return {
        "redis_monitoring": {
            "metrics": ["used_memory", "connected_clients", "total_commands_processed"],
            "thresholds": {"max_memory_usage": "1GB", "max_clients": 1000, "min_hit_rate": 80.0},
            "sample_interval": 60,
        }
    }


@pytest.fixture
def sample_info():
    """Sample Redis INFO command output."""
    return {
        "used_memory": "1048576",
        "used_memory_peak": "2097152",
        "connected_clients": "10",
        "total_commands_processed": "1000",
        "keyspace_hits": "800",
        "keyspace_misses": "200",
    }


def test_collect_metrics_success(mock_redis, sample_info):
    """Test successful metrics collection."""
    mock_redis.info.return_value = sample_info
    metrics = ["used_memory", "connected_clients"]

    result = collect_metrics(mock_redis, metrics)

    assert "used_memory" in result
    assert "connected_clients" in result
    assert result["used_memory"] == "1048576"
    assert result["connected_clients"] == "10"
    mock_redis.info.assert_called_once()


def test_collect_metrics_partial_metrics(mock_redis, sample_info):
    """Test metrics collection with some metrics missing."""
    mock_redis.info.return_value = sample_info
    metrics = ["used_memory", "nonexistent_metric"]

    result = collect_metrics(mock_redis, metrics)

    assert "used_memory" in result
    assert "nonexistent_metric" in result
    assert result["used_memory"] == "1048576"
    assert result["nonexistent_metric"] == 0


def test_collect_metrics_redis_error(mock_redis):
    """Test metrics collection with Redis error."""
    mock_redis.info.side_effect = Exception("Redis error")
    metrics = ["used_memory"]

    with pytest.raises(Exception) as exc:
        collect_metrics(mock_redis, metrics)
    assert "Redis error" in str(exc.value)


@patch("argparse.ArgumentParser.parse_args")
@patch("time.sleep", return_value=None)
@patch("time.time")
@patch("builtins.open", new_callable=mock_open)
def test_main_success(mock_file, mock_time, mock_sleep, mock_args, mock_redis, sample_config):
    """Test successful execution of main function."""
    # Setup mock arguments
    mock_args.return_value = MagicMock(
        config="config.json", output="metrics.log", duration=5, host="localhost", port=6379
    )

    # Setup mock time to run loop twice
    mock_time.side_effect = [0, 1, 2, 6]

    # Setup mock file operations
    mock_config_data = json.dumps(sample_config)
    mock_file.return_value.__enter__.return_value.read.return_value = mock_config_data

    # Setup mock Redis info
    mock_redis.info.return_value = {
        "used_memory": "1048576",
        "connected_clients": "10",
        "total_commands_processed": "1000",
    }

    with patch(
        "sys.argv",
        ["script.py", "--config", "config.json", "--output", "metrics.log", "--duration", "5"],
    ):
        main()

    # Verify file operations
    assert mock_file.call_count >= 2  # One for config read, at least one for metrics write
    mock_file().write.assert_called()


@patch("argparse.ArgumentParser.parse_args")
def test_main_config_error(mock_args, mock_redis):
    """Test main function with configuration error."""
    mock_args.return_value = MagicMock(
        config="nonexistent.json", output="metrics.log", duration=5, host="localhost", port=6379
    )

    with patch(
        "sys.argv",
        ["script.py", "--config", "nonexistent.json", "--output", "metrics.log", "--duration", "5"],
    ):
        with pytest.raises(SystemExit):
            main()


@patch("argparse.ArgumentParser.parse_args")
@patch("time.sleep", side_effect=KeyboardInterrupt)
def test_main_keyboard_interrupt(mock_sleep, mock_args, mock_redis, sample_config):
    """Test main function handling keyboard interrupt."""
    mock_args.return_value = MagicMock(
        config="config.json", output="metrics.log", duration=5, host="localhost", port=6379
    )

    with patch("builtins.open", mock_open(read_data=json.dumps(sample_config))):
        with pytest.raises(SystemExit):
            main()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
