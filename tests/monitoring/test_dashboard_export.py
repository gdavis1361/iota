import json
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.monitoring.export_dashboards import GrafanaExporter


@pytest.fixture
def mock_dashboard_list():
    return [
        {
            "id": 1,
            "uid": "abc123",
            "title": "Test Dashboard",
            "url": "/d/abc123"
        }
    ]

@pytest.fixture
def mock_dashboard_data():
    return {
        "dashboard": {
            "id": 1,
            "uid": "abc123",
            "title": "Test Dashboard",
            "version": 1,
            "panels": [
                {
                    "id": 1,
                    "title": "Test Panel",
                    "type": "graph"
                }
            ]
        },
        "meta": {
            "isFolder": False,
            "folderId": 0
        }
    }

@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock_get:
        yield mock_get

def test_get_all_dashboards(mock_requests, mock_dashboard_list):
    mock_requests.return_value.json.return_value = mock_dashboard_list
    mock_requests.return_value.raise_for_status = MagicMock()
    
    exporter = GrafanaExporter("http://localhost:3000", "test-key")
    dashboards = exporter.get_all_dashboards()
    
    assert len(dashboards) == 1
    assert dashboards[0]["uid"] == "abc123"
    mock_requests.assert_called_once_with(
        "http://localhost:3000/api/search?type=dash-db",
        headers={
            'Authorization': 'Bearer test-key',
            'Content-Type': 'application/json'
        }
    )

def test_get_dashboard(mock_requests, mock_dashboard_data):
    mock_requests.return_value.json.return_value = mock_dashboard_data
    mock_requests.return_value.raise_for_status = MagicMock()
    
    exporter = GrafanaExporter("http://localhost:3000", "test-key")
    dashboard = exporter.get_dashboard("abc123")
    
    assert dashboard["dashboard"]["uid"] == "abc123"
    mock_requests.assert_called_once_with(
        "http://localhost:3000/api/dashboards/uid/abc123",
        headers={
            'Authorization': 'Bearer test-key',
            'Content-Type': 'application/json'
        }
    )

def test_export_dashboards(mock_requests, mock_dashboard_list, mock_dashboard_data, tmp_path):
    mock_requests.return_value.raise_for_status = MagicMock()
    mock_requests.side_effect = [
        MagicMock(json=lambda: mock_dashboard_list),
        MagicMock(json=lambda: mock_dashboard_data)
    ]
    
    output_dir = str(tmp_path / "dashboards")
    exporter = GrafanaExporter("http://localhost:3000", "test-key")
    exporter.export_dashboards(output_dir, backup=True)
    
    # Check main export
    assert os.path.exists(output_dir)
    dashboard_file = os.path.join(output_dir, "abc123.json")
    assert os.path.exists(dashboard_file)
    
    # Verify file contents
    with open(dashboard_file) as f:
        data = json.load(f)
        assert "version" not in data["dashboard"]
        assert "id" not in data["dashboard"]
        assert data["dashboard"]["uid"] == "abc123"
    
    # Check backup
    backup_dirs = [d for d in os.listdir(output_dir) if d.startswith("backup_")]
    assert len(backup_dirs) == 1
    backup_file = os.path.join(output_dir, backup_dirs[0], "abc123.json")
    assert os.path.exists(backup_file)

@pytest.mark.parametrize("error_type", [
    requests.ConnectionError,
    requests.Timeout,
    requests.RequestException
])
def test_error_handling(mock_requests, error_type, tmp_path):
    mock_requests.side_effect = error_type("Test error")
    
    output_dir = str(tmp_path / "dashboards")
    exporter = GrafanaExporter("http://localhost:3000", "test-key")
    
    with pytest.raises(Exception):
        exporter.export_dashboards(output_dir)

def test_invalid_api_key(mock_requests, tmp_path):
    mock_requests.return_value.raise_for_status.side_effect = requests.HTTPError("401 Client Error: Unauthorized")
    
    output_dir = str(tmp_path / "dashboards")
    exporter = GrafanaExporter("http://localhost:3000", "invalid-key")
    
    with pytest.raises(requests.HTTPError):
        exporter.export_dashboards(output_dir)

def test_url_handling():
    # Test trailing slash handling
    exporter1 = GrafanaExporter("http://localhost:3000/", "test-key")
    exporter2 = GrafanaExporter("http://localhost:3000", "test-key")
    
    assert exporter1.grafana_url == "http://localhost:3000"
    assert exporter2.grafana_url == "http://localhost:3000"
