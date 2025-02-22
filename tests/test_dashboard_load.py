"""Load testing suite for Grafana dashboards."""

import asyncio
import json
import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import pytest
import pytest_asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from scripts.metrics_exporter import ValidationMetricsExporter


class TestDashboardLoad:
    @pytest.fixture(scope="session")
    def grafana_url(self):
        """Grafana dashboard URL."""
        return "http://localhost:3000"

    @pytest.fixture(scope="session")
    def grafana_auth(self):
        """Grafana authentication."""
        return ("admin", "admin")

    @pytest.fixture(scope="session")
    def metrics_exporter(self):
        """Initialize metrics exporter."""
        exporter = ValidationMetricsExporter(port=9090)
        exporter.start()
        return exporter

    class MockGrafanaServer:
        """Context manager for mock Grafana server."""

        def __init__(self):
            self.app = None
            self.runner = None
            self.site = None

        async def __aenter__(self):
            """Start the mock server."""
            from aiohttp import web

            async def handle_dashboard(request):
                await asyncio.sleep(0.01)  # Simulate processing time
                return web.json_response(
                    {
                        "dashboard": {
                            "id": 1,
                            "uid": "validation-dashboard",
                            "title": "Validation Dashboard",
                        }
                    }
                )

            async def handle_panel_data(request):
                await asyncio.sleep(0.02)  # Simulate processing time
                return web.json_response(
                    {
                        "data": {
                            "result": [
                                {
                                    "metric": {"__name__": "test_metric"},
                                    "values": [[1000000000, "1"], [2000000000, "2"]],
                                }
                            ]
                        }
                    }
                )

            self.app = web.Application()
            self.app.router.add_get("/api/dashboards/uid/{uid}", handle_dashboard)
            self.app.router.add_get(
                "/api/datasources/proxy/1/api/v1/query_range", handle_panel_data
            )

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "localhost", 3000)
            await self.site.start()
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Clean up the mock server."""
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()

    @pytest_asyncio.fixture(scope="session")
    async def mock_grafana_server(self):
        """Provide mock Grafana server as a fixture."""
        async with TestDashboardLoad.MockGrafanaServer() as server:
            await asyncio.sleep(0.1)  # Wait for server to start
            yield server

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def fetch_dashboard(self, session, url, auth, timing_queue):
        """Fetch dashboard data with retry logic."""
        before = time.time()
        try:
            async with session.get(url, auth=aiohttp.BasicAuth(*auth)) as response:
                data = await response.json()
                elapsed = time.time() - before
                await timing_queue.put(elapsed)
                return data, response.status, elapsed
        except Exception as e:
            print(f"Error fetching dashboard: {e}")
            raise

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    async def fetch_panel_data(self, session, url, panel_id, auth, start, end, timing_queue):
        """Fetch panel data with retry logic."""
        query_url = f"{url}/api/datasources/proxy/1/api/v1/query_range"
        params = {
            "query": f"panel_{panel_id}",
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": "15s",
        }
        before = time.time()
        try:
            async with session.get(
                query_url, params=params, auth=aiohttp.BasicAuth(*auth)
            ) as response:
                data = await response.json()
                elapsed = time.time() - before
                await timing_queue.put(elapsed)
                return data, response.status, elapsed
        except Exception as e:
            print(f"Error fetching panel data: {e}")
            raise

    def generate_test_data(self, metrics_exporter, num_points=100):
        """Generate test data points."""
        metrics = {
            "error_count": 0,
            "warning_count": 0,
            "security_count": 0,
            "validation_time_ms": 0,
            "last_validation": "2024-03-14T00:00:00Z",
        }

        for i in range(num_points):
            metrics["error_count"] += 1
            metrics["warning_count"] += 1
            if i % 10 == 0:  # 10% security issues
                metrics["security_count"] += 1
            metrics["validation_time_ms"] = (
                10 * num_points
            )  # Simulate longer validation for more points

        metrics_file = Path("tests/validation_metrics.json")
        with open(metrics_file, "w") as f:
            json.dump(metrics, f)

        metrics_exporter.update_metrics(metrics_file)

    async def simulate_concurrent_users(
        self, num_users, duration_seconds, grafana_url, grafana_auth
    ):
        """Simulate multiple users accessing the dashboard."""
        timing_queue = asyncio.Queue()
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            error_count = 0

            while time.time() - start_time < duration_seconds:
                tasks = []
                for _ in range(num_users):
                    task = asyncio.create_task(
                        self.fetch_dashboard(
                            session,
                            f"{grafana_url}/api/dashboards/uid/validation-dashboard",
                            grafana_auth,
                            timing_queue,
                        )
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1

                await asyncio.sleep(1)  # Wait before next batch

            # Collect all timing data
            request_times = []
            while not timing_queue.empty():
                request_times.append(await timing_queue.get())

            return request_times, error_count

    @pytest.mark.asyncio
    async def test_dashboard_load(
        self, grafana_url, grafana_auth, metrics_exporter, mock_grafana_server
    ):
        """Test dashboard performance under load."""
        # Generate test data
        self.generate_test_data(metrics_exporter)

        # Test parameters
        num_users = 10
        duration = 5  # Reduced for faster testing

        # Run load test
        request_times, errors = await self.simulate_concurrent_users(
            num_users, duration, grafana_url, grafana_auth
        )

        # Calculate metrics
        assert len(request_times) > 0, "No request timing data collected"
        avg_response = statistics.mean(request_times)
        p95_response = statistics.quantiles(request_times, n=20)[18]  # 95th percentile
        error_rate = errors / (len(request_times) + errors)

        # Assert performance requirements
        assert avg_response < 1.0, f"Average response time {avg_response:.2f}s exceeds 1s threshold"
        assert (
            p95_response < 2.0
        ), f"95th percentile response time {p95_response:.2f}s exceeds 2s threshold"
        assert error_rate < 0.01, f"Error rate {error_rate:.2%} exceeds 1% threshold"

    @pytest.mark.asyncio
    async def test_panel_refresh(
        self, grafana_url, grafana_auth, metrics_exporter, mock_grafana_server
    ):
        """Test panel refresh performance."""
        timing_queue = asyncio.Queue()

        # Generate test data
        self.generate_test_data(metrics_exporter)

        async with aiohttp.ClientSession() as session:
            end = datetime.utcnow()
            start = end - timedelta(minutes=5)

            panels = ["errors", "warnings", "security", "duration", "timestamp"]
            tasks = []

            for panel in panels:
                task = asyncio.create_task(
                    self.fetch_panel_data(
                        session, grafana_url, panel, grafana_auth, start, end, timing_queue
                    )
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # Collect timing data
            panel_times = []
            while not timing_queue.empty():
                panel_times.append(await timing_queue.get())

            # Verify panel data
            assert len(panel_times) == len(panels), "Not all panel timings collected"
            for (data, status, _), panel, elapsed in zip(results, panels, panel_times):
                assert status == 200, f"Panel {panel} failed to load"
                assert elapsed < 1.0, f"Panel {panel} took too long to load: {elapsed:.2f}s"
                assert "data" in data, f"Panel {panel} returned no data"

    def test_memory_usage(self, grafana_url, grafana_auth, metrics_exporter):
        """Test memory usage during dashboard operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate significant test data
        self.generate_test_data(metrics_exporter, num_points=10000)

        # Measure memory after data generation
        data_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = data_memory - initial_memory

        assert (
            memory_increase < 100
        ), f"Memory usage increased by {memory_increase:.1f}MB (max: 100MB)"
