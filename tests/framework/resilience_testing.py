"""Comprehensive testing framework for resilience testing."""
import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from redis.sentinel import Sentinel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ScenarioConfig:
    """Configuration for a test scenario."""

    name: str
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    assertions: List[Callable] = None
    timeout: int = 30
    retry_count: int = 3
    cleanup_required: bool = True


class MetricsCollector:
    """Collects and analyzes test metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @asynccontextmanager
    async def measure(self):
        """Context manager for measuring execution time."""
        self.start_time = datetime.utcnow()
        try:
            yield
        finally:
            self.end_time = datetime.utcnow()
            duration = (self.end_time - self.start_time).total_seconds()
            self.record_metric("execution_time", duration)

    def record_metric(self, name: str, value: float):
        """Record a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)

    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get summary of collected metrics."""
        summary = {}
        for name, values in self.metrics.items():
            summary[name] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values),
            }
        return summary


class DatabaseManager:
    """Manages database state for tests."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.savepoints: List[str] = []

    async def create_savepoint(self) -> str:
        """Create a new savepoint."""
        savepoint = f"sp_{len(self.savepoints)}"
        await self.session.execute(f"SAVEPOINT {savepoint}")
        self.savepoints.append(savepoint)
        return savepoint

    async def rollback_to_savepoint(self, savepoint: str):
        """Rollback to a specific savepoint."""
        if savepoint in self.savepoints:
            await self.session.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            idx = self.savepoints.index(savepoint)
            self.savepoints = self.savepoints[: idx + 1]


class ChaosEngine:
    """Simulates various failure scenarios."""

    def __init__(self):
        self.original_states: Dict[str, Any] = {}

    async def simulate_network_latency(self, delay_ms: int):
        """Simulate network latency."""
        await asyncio.sleep(delay_ms / 1000)

    async def simulate_redis_failure(self, sentinel: Sentinel):
        """Simulate Redis master failure."""
        master_info = sentinel.discover_master("mymaster")
        if master_info:
            host, port = master_info
            # Store original state
            self.original_states["redis_master"] = (host, port)
            # Simulate failure by changing to invalid host
            sentinel._master_for["mymaster"] = ("invalid_host", port)

    async def restore_redis(self, sentinel: Sentinel):
        """Restore Redis to original state."""
        if "redis_master" in self.original_states:
            host, port = self.original_states["redis_master"]
            sentinel._master_for["mymaster"] = (host, port)
            del self.original_states["redis_master"]


class ResilienceTestFramework:
    """Framework for testing system resilience."""

    def __init__(self, db_session: AsyncSession):
        self.scenarios: Dict[str, ScenarioConfig] = {}
        self.metrics_collector = MetricsCollector()
        self.chaos_engine = ChaosEngine()
        self.db_manager = DatabaseManager(db_session)

    def register_scenario(self, config: ScenarioConfig):
        """Register a new test scenario."""
        self.scenarios[config.name] = config

    async def run_scenario(self, name: str) -> Dict[str, Any]:
        """Run a specific test scenario."""
        if name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {name}")

        config = self.scenarios[name]
        results = {"name": name, "success": False, "errors": [], "metrics": {}}

        # Create savepoint for potential rollback
        savepoint = await self.db_manager.create_savepoint()

        try:
            # Setup
            if config.setup:
                await config.setup()

            # Run scenario with metrics collection
            async with self.metrics_collector.measure():
                for assertion in config.assertions:
                    try:
                        await assertion()
                    except AssertionError as e:
                        results["errors"].append(str(e))

            results["success"] = len(results["errors"]) == 0
            results["metrics"] = self.metrics_collector.get_metrics()

        except Exception as e:
            results["errors"].append(f"Scenario failed: {str(e)}")

        finally:
            # Cleanup
            if config.cleanup_required:
                await self.db_manager.rollback_to_savepoint(savepoint)
                if config.teardown:
                    await config.teardown()

        return results

    async def run_all_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered scenarios."""
        results = {}
        for name in self.scenarios:
            results[name] = await self.run_scenario(name)
        return results
