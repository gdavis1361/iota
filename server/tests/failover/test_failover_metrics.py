import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pytest
import redis.asyncio as redis
from redis.sentinel import MasterNotFoundError, Sentinel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_CONFIG = {
    "sentinels": [
        ("172.19.0.4", 26379),  # redis-sentinel-1
        ("172.19.0.5", 26379),  # redis-sentinel-2
        ("172.19.0.6", 26379),  # redis-sentinel-3
    ],
    "master_name": "mymaster",
    "socket_timeout": 0.1,  # Reduced timeout for faster failover detection
    "retry_on_timeout": True,
}

# Performance thresholds
THRESHOLDS = {
    "max_failover_detection_time": 3.0,  # seconds
    "max_total_failover_time": 5.0,  # seconds
    "min_write_success_rate": 95.0,  # percent
    "min_sentinel_quorum": 2,  # number of sentinels
    "max_write_failure_window": 2.0,  # seconds of continuous write failures
}


class PerformanceValidationError(Exception):
    """Raised when performance metrics don't meet thresholds."""

    pass


@dataclass
class FailoverMetrics:
    """Enhanced metrics with threshold validation."""

    start_time: float
    detection_time: Optional[float] = None
    promotion_time: Optional[float] = None
    recovery_time: Optional[float] = None
    write_success: int = 0
    write_failures: int = 0
    events: List[Dict] = None

    def __post_init__(self):
        self.events = []

    def add_event(self, event_type: str, details: str = None):
        """Add timestamped event with structured logging."""
        timestamp = time.time()
        event = {
            "timestamp": timestamp,
            "relative_time": timestamp - self.start_time,
            "type": event_type,
            "details": details,
        }
        self.events.append(event)
        logger.info(
            f"Event: {event_type}",
            extra={
                "event_type": event_type,
                "details": details,
                "relative_time": event["relative_time"],
            },
        )

    def validate_performance(self) -> List[str]:
        """Validate metrics against defined thresholds."""
        violations = []

        # Check failover detection time
        if self.detection_time:
            detection_duration = self.detection_time - self.start_time
            if detection_duration > THRESHOLDS["max_failover_detection_time"]:
                violations.append(
                    f"Failover detection took {detection_duration:.2f}s "
                    f"(max: {THRESHOLDS['max_failover_detection_time']}s)"
                )

        # Check total failover time
        if self.recovery_time:
            total_duration = self.recovery_time - self.start_time
            if total_duration > THRESHOLDS["max_total_failover_time"]:
                violations.append(
                    f"Total failover took {total_duration:.2f}s "
                    f"(max: {THRESHOLDS['max_total_failover_time']}s)"
                )

        # Check write success rate
        total_writes = self.write_success + self.write_failures
        if total_writes > 0:
            success_rate = (self.write_success / total_writes) * 100
            if success_rate < THRESHOLDS["min_write_success_rate"]:
                violations.append(
                    f"Write success rate {success_rate:.1f}% "
                    f"below minimum {THRESHOLDS['min_write_success_rate']}%"
                )

        return violations


class ConcurrentWriter:
    """Concurrent write testing with metrics."""

    def __init__(self, metrics: FailoverMetrics):
        self.metrics = metrics
        self.running = True
        self.sentinel = Sentinel(
            REDIS_CONFIG["sentinels"],
            socket_timeout=REDIS_CONFIG["socket_timeout"],
            retry_on_timeout=REDIS_CONFIG["retry_on_timeout"],
        )

    async def write_loop(self):
        """Continuous write loop with metrics."""
        key_base = f"test:concurrent:{int(time.time())}"
        counter = 0
        redis_client = None

        while self.running:
            try:
                if redis_client is None:
                    # Get current master
                    master = await self.sentinel.discover_master(REDIS_CONFIG["master_name"])
                    redis_client = await redis.Redis(
                        host=master[0], port=master[1], decode_responses=True
                    )

                # Perform write
                key = f"{key_base}:{counter}"
                value = f"value-{counter}-{datetime.now().isoformat()}"
                await redis_client.set(key, value)

                self.metrics.write_success += 1
                counter += 1

            except Exception:
                self.metrics.write_failures += 1
                self.metrics.add_event("write_error")
                redis_client = None
                await asyncio.sleep(0.1)

            await asyncio.sleep(0.01)

        if redis_client:
            await redis_client.close()

    def stop(self):
        """Stop the write loop."""
        self.running = False


class FailoverTestSuite:
    """Enhanced failover test suite with performance validation."""

    def __init__(self):
        self.metrics = FailoverMetrics(start_time=time.time())
        self.sentinel = Sentinel(
            REDIS_CONFIG["sentinels"],
            socket_timeout=REDIS_CONFIG["socket_timeout"],
            retry_on_timeout=REDIS_CONFIG["retry_on_timeout"],
        )

    async def get_master_info(self) -> Optional[Tuple[str, int]]:
        """Get current master with retry logic."""
        for _ in range(3):  # Retry up to 3 times
            try:
                return self.sentinel.discover_master(REDIS_CONFIG["master_name"])
            except MasterNotFoundError:
                await asyncio.sleep(0.1)
        return None

    async def test_concurrent_failover(self):
        """Test failover with concurrent writes and performance validation."""
        try:
            # Initial state
            initial_master = await self.get_master_info()
            if not initial_master:
                raise Exception("Could not discover initial master")

            self.metrics.add_event("initial_state", f"Initial master: {initial_master}")

            # Start concurrent writes
            writer = ConcurrentWriter(self.metrics)
            write_task = asyncio.create_task(writer.write_loop())

            await asyncio.sleep(3)  # Allow writes to stabilize

            # Initiate master shutdown
            self.metrics.add_event("master_shutdown", "Shutting down master")
            try:
                redis_client = await redis.Redis(
                    host=initial_master[0],
                    port=initial_master[1],
                    socket_timeout=1,
                    decode_responses=True,
                )
                await redis_client.shutdown(nosave=True)
                await redis_client.close()
            except Exception:
                self.metrics.add_event("shutdown_error")

            # Monitor failover
            detection_start = time.time()
            new_master = None
            while time.time() - detection_start < 10:
                try:
                    current_master = await self.get_master_info()
                    if current_master and current_master != initial_master:
                        new_master = current_master
                        self.metrics.detection_time = time.time()
                        self.metrics.add_event("failover_detected", f"New master: {new_master}")
                        break
                except Exception:
                    await asyncio.sleep(0.1)

            if not new_master:
                raise Exception("Failover did not complete within timeout")

            # Verify stability
            await asyncio.sleep(5)

            # Complete test
            writer.stop()
            await write_task
            self.metrics.recovery_time = time.time()

            # Validate performance
            violations = self.metrics.validate_performance()
            if violations:
                raise PerformanceValidationError(
                    "Performance thresholds violated:\n" + "\n".join(f"- {v}" for v in violations)
                )

            return True

        except PerformanceValidationError as e:
            logger.error("Performance validation failed: %s", str(e))
            self.metrics.add_event("performance_validation_failed", str(e))
            return False

        except Exception:
            logger.error("Test failure")
            self.metrics.add_event("test_error")
            return False

    def print_report(self):
        """Generate comprehensive test report."""
        print("\n=== Enhanced Failover Test Report ===")

        # Print event timeline
        print("\nEvent Timeline:")
        for event in self.metrics.events:
            elapsed = event["timestamp"] - self.metrics.start_time
            print(f"{elapsed:.3f}s - {event['type']}: {event['details']}")

        # Print write statistics
        total_writes = self.metrics.write_success + self.metrics.write_failures
        if total_writes > 0:
            success_rate = (self.metrics.write_success / total_writes) * 100
            print(
                f"\nWrite Statistics:\n"
                f"Success: {self.metrics.write_success}\n"
                f"Failures: {self.metrics.write_failures}\n"
                f"Success Rate: {success_rate:.1f}%"
            )

        # Print performance validation
        try:
            violations = self.metrics.validate_performance()
            if not violations:
                print("\n✅ All performance thresholds met!")
            else:
                print("\n❌ Performance thresholds violated:")
                for violation in violations:
                    print(f"- {violation}")
        except Exception as e:
            print("\n⚠️ Error validating performance:", str(e))

        # Print detection and recovery times
        if self.metrics.detection_time:
            detection_time = self.metrics.detection_time - self.metrics.start_time
            print(f"\nDetection Time: {detection_time:.3f}s")

        if self.metrics.recovery_time:
            total_time = self.metrics.recovery_time - self.metrics.start_time
            print(f"Total Duration: {total_time:.3f}s")

        # Export metrics
        with open("failover_metrics.json", "w") as f:
            json.dump(asdict(self.metrics), f, indent=2)


@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_failover_with_monitoring():
    """Main test with performance validation."""
    suite = FailoverTestSuite()
    success = await suite.test_concurrent_failover()
    suite.print_report()
    assert success, "Failover test failed performance validation"
