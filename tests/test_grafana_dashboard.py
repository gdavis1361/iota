"""Integration tests for Grafana dashboard configuration and visualization."""

import json
import time
from datetime import datetime, timedelta

import pytest
import requests

from scripts.metrics_exporter import ConfigValidationMetrics


class TestGrafanaDashboard:
    @pytest.fixture
    def grafana_api_url(self):
        """Grafana API endpoint."""
        return "http://localhost:3000/api"

    @pytest.fixture
    def grafana_auth(self):
        """Grafana authentication."""
        return ("admin", "admin")

    @pytest.fixture
    def dashboard_path(self):
        """Path to dashboard configuration."""
        return "/config/grafana/validation_dashboard.json"

    @pytest.fixture
    def metrics_exporter(self):
        """Initialize metrics exporter."""
        return ConfigValidationMetrics()

    def test_dashboard_json_validity(self, dashboard_path):
        """Test dashboard JSON is valid and contains required panels."""
        with open(dashboard_path) as f:
            dashboard = json.load(f)

        # Verify basic structure
        assert "dashboard" in dashboard
        assert "panels" in dashboard["dashboard"]

        # Check required panels exist
        panel_titles = [p.get("title") for p in dashboard["dashboard"]["panels"]]
        required_panels = [
            "Configuration Validation Errors",
            "Configuration Validation Warnings",
            "Security Issues",
            "Validation Duration",
            "Last Validation Time",
        ]
        for panel in required_panels:
            assert panel in panel_titles

    def test_dashboard_alert_rules(self, dashboard_path):
        """Test alert rules are properly configured."""
        with open(dashboard_path) as f:
            dashboard = json.load(f)

        alerts = []
        for panel in dashboard["dashboard"]["panels"]:
            if "alert" in panel:
                alerts.append(panel["alert"])

        # Verify alert configurations
        alert_names = [a.get("name") for a in alerts]
        required_alerts = [
            "High Error Rate",
            "Excessive Warnings",
            "Security Issue Detected",
            "Stale Validation",
        ]
        for alert in required_alerts:
            assert alert in alert_names

        # Check alert thresholds
        for alert in alerts:
            if alert["name"] == "High Error Rate":
                assert "config_validation_errors > 10" in alert["conditions"][0]["query"]["expr"]
            elif alert["name"] == "Excessive Warnings":
                assert "config_validation_warnings > 20" in alert["conditions"][0]["query"]["expr"]
            elif alert["name"] == "Security Issue Detected":
                assert (
                    "config_validation_security_issues > 0"
                    in alert["conditions"][0]["query"]["expr"]
                )
            elif alert["name"] == "Stale Validation":
                assert (
                    "time() - config_validation_last_timestamp > 900"
                    in alert["conditions"][0]["query"]["expr"]
                )

    def test_dashboard_api_integration(self, grafana_api_url, grafana_auth):
        """Test dashboard can be loaded via Grafana API."""
        response = requests.get(
            f"{grafana_api_url}/dashboards/uid/validation-dashboard", auth=grafana_auth
        )
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard["dashboard"]["title"] == "Configuration Validation"

    def test_metric_visualization(self, metrics_exporter, grafana_api_url, grafana_auth):
        """Test metrics appear in Grafana visualizations."""
        # Generate test data
        metrics_exporter.record_validation_error()
        metrics_exporter.record_validation_warning()
        metrics_exporter.record_security_issue()

        with metrics_exporter.track_validation_duration():
            time.sleep(0.1)

        # Query Grafana for metrics
        end = datetime.utcnow()
        start = end - timedelta(minutes=5)

        query_params = {
            "query": "config_validation_errors",
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": 15,
        }

        response = requests.get(
            f"{grafana_api_url}/datasources/proxy/1/api/v1/query_range",
            params=query_params,
            auth=grafana_auth,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["result"]) > 0

    def test_dashboard_refresh(self, grafana_api_url, grafana_auth, dashboard_path):
        """Test dashboard refresh settings."""
        with open(dashboard_path) as f:
            dashboard = json.load(f)

        # Verify refresh interval
        assert dashboard["dashboard"]["refresh"] in ["5s", "10s", "30s"]

        # Check time range
        time_range = dashboard["dashboard"]["time"]
        assert "from" in time_range
        assert "to" in time_range

    def test_dashboard_variables(self, dashboard_path):
        """Test dashboard template variables."""
        with open(dashboard_path) as f:
            dashboard = json.load(f)

        variables = dashboard["dashboard"].get("templating", {}).get("list", [])

        # Check for required variables
        var_names = [v.get("name") for v in variables]
        required_vars = ["environment", "interval"]

        for var in required_vars:
            assert var in var_names

    def test_panel_data_sources(self, dashboard_path):
        """Test panel data source configurations."""
        with open(dashboard_path) as f:
            dashboard = json.load(f)

        for panel in dashboard["dashboard"]["panels"]:
            if "datasource" in panel:
                assert panel["datasource"]["type"] == "prometheus"
                assert "uid" in panel["datasource"]

    def test_dashboard_permissions(self, grafana_api_url, grafana_auth):
        """Test dashboard permissions are properly set."""
        response = requests.get(
            f"{grafana_api_url}/dashboards/uid/validation-dashboard/permissions", auth=grafana_auth
        )
        assert response.status_code == 200
        permissions = response.json()

        # Verify basic permission structure
        assert isinstance(permissions, list)
        assert len(permissions) > 0

        # Check for required roles
        roles = [p.get("role") for p in permissions]
        assert "Viewer" in roles
        assert "Editor" in roles
