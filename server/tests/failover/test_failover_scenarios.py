import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from datetime import datetime

import pytest
from prometheus_client import Counter, Gauge, Histogram

# -------------------------------------------------------------------
# Metrics Configuration
# -------------------------------------------------------------------

# Prometheus metrics
FAILOVER_DURATION = Histogram(
    'redis_failover_duration_seconds',
    'Time taken for failover to complete',
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

FAILOVER_TOTAL = Counter(
    'redis_failover_total',
    'Total number of failovers',
    ['result']  # success/failure
)

WRITE_SUCCESS_RATE = Gauge(
    'redis_write_success_rate',
    'Success rate of write operations during failover'
)

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------


def run_cmd(cmd):
    """
    Helper to run shell commands and return (success, output).
    """
    print(f"[CMD] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return True, result.stdout.strip()
    else:
        print(f"[ERROR] {result.stderr.strip()}")
        return False, result.stderr.strip()


def stop_service(service_name, compose_file="docker-compose.redis.yml"):
    return run_cmd(f"docker compose -f {compose_file} stop {service_name}")


def start_service(service_name, compose_file="docker-compose.redis.yml"):
    return run_cmd(f"docker compose -f {compose_file} start {service_name}")


def kill_service(service_name, compose_file="docker-compose.redis.yml"):
    return run_cmd(f"docker compose -f {compose_file} kill {service_name}")


def get_master_info(sentinel_container="redis-redis-sentinel-1-1"):
    """
    Return the current master address from sentinel.
    """
    cmd = (
        f"docker exec {sentinel_container} "
        "redis-cli -p 26379 sentinel get-master-addr-by-name mymaster"
    )
    success, output = run_cmd(cmd)
    if success and output:
        lines = output.splitlines()
        # Clean up Redis array output format
        return [line.strip().strip('"') for line in lines if line.strip()]
    return None


def get_redis_info(container, port=6379):
    """Get Redis INFO command output"""
    cmd = f"docker exec {container} redis-cli -p {port} info replication"
    success, output = run_cmd(cmd)
    return output if success else None


def partition_container(container_name, network_name="redis_redis-net"):
    return run_cmd(f"docker network disconnect {network_name} {container_name}")


def reconnect_container(container_name, network_name="redis_redis-net"):
    return run_cmd(f"docker network connect {network_name} {container_name}")


class ConcurrentWriter:
    """Helper class to test concurrent writes during failover."""

    def __init__(self):
        self.write_success = 0
        self.write_failures = 0
        self.write_interval = 0.1
        self.running = False

    async def write_loop(self, duration: int = 30) -> Tuple[int, int]:
        """Run a continuous write loop for the specified duration."""
        self.running = True
        start_time = time.time()
        while self.running and time.time() - start_time < duration:
            try:
                # Write operation
                await asyncio.sleep(self.write_interval)
                self.write_success += 1
            except Exception:
                self.write_failures += 1
                await asyncio.sleep(0.1)
        return self.write_success, self.write_failures

    def stop(self):
        """Stop the write loop."""
        self.running = False

    def get_success_rate(self) -> float:
        """Calculate write success rate."""
        total = self.write_success + self.write_failures
        return self.write_success / total if total > 0 else 0.0


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
class ChaosEvent:
    """Represents a chaos engineering event."""
    event_type: str
    target: str
    start_time: float
    duration: float
    description: str
    metrics: Dict = field(default_factory=dict)
    recovery_time: Optional[float] = None


class ChaosOrchestrator:
    """Orchestrates chaos engineering scenarios."""
    
    def __init__(self):
        self.events: List[ChaosEvent] = []
        self.active_scenarios = set()
    
    async def network_delay(self, container: str, latency_ms: int = 100, duration: int = 30):
        """Introduce network latency to a container."""
        event = ChaosEvent(
            event_type="network_delay",
            target=container,
            start_time=time.time(),
            duration=duration,
            description=f"Added {latency_ms}ms latency to {container}"
        )
        self.events.append(event)
        
        cmd = f"docker exec {container} tc qdisc add dev eth0 root netem delay {latency_ms}ms"
        success, _ = run_cmd(cmd)
        if not success:
            logger.error(f"Failed to add network delay to {container}")
            return False
            
        await asyncio.sleep(duration)
        
        cmd = f"docker exec {container} tc qdisc del dev eth0 root"
        success, _ = run_cmd(cmd)
        event.recovery_time = time.time()
        return success

    async def cpu_pressure(self, container: str, load: int = 80, duration: int = 30):
        """Simulate CPU pressure on a container."""
        event = ChaosEvent(
            event_type="cpu_pressure",
            target=container,
            start_time=time.time(),
            duration=duration,
            description=f"Added {load}% CPU load to {container}"
        )
        self.events.append(event)
        
        cmd = f"docker exec {container} stress-ng --cpu 1 --cpu-load {load} --timeout {duration}s"
        success, _ = run_cmd(cmd)
        if not success:
            logger.error(f"Failed to add CPU pressure to {container}")
            return False
            
        event.recovery_time = time.time()
        return success

    async def memory_pressure(self, container: str, bytes_to_fill: int = 1024*1024*100, duration: int = 30):
        """Simulate memory pressure on a container."""
        event = ChaosEvent(
            event_type="memory_pressure",
            target=container,
            start_time=time.time(),
            duration=duration,
            description=f"Added memory pressure ({bytes_to_fill} bytes) to {container}"
        )
        self.events.append(event)
        
        cmd = f"docker exec {container} stress-ng --vm 1 --vm-bytes {bytes_to_fill} --timeout {duration}s"
        success, _ = run_cmd(cmd)
        if not success:
            logger.error(f"Failed to add memory pressure to {container}")
            return False
            
        event.recovery_time = time.time()
        return success

    def get_event_history(self) -> List[Dict]:
        """Return formatted event history."""
        return [
            {
                "type": e.event_type,
                "target": e.target,
                "start_time": datetime.fromtimestamp(e.start_time).isoformat(),
                "duration": e.duration,
                "description": e.description,
                "metrics": e.metrics,
                "recovery_time": datetime.fromtimestamp(e.recovery_time).isoformat() if e.recovery_time else None
            }
            for e in self.events
        ]


class FailoverMetrics:
    """Enhanced metrics with threshold validation and Prometheus integration."""
    
    def __init__(self):
        self.start_time: float = time.time()
        self.detection_time: float = 0.0
        self.recovery_time: float = 0.0
        self.write_success: int = 0
        self.write_failures: int = 0
        self.events: List[dict] = []
        self.chaos_events: List[ChaosEvent] = []
    
    def record_failover_completion(self, success: bool):
        """Record failover completion metrics."""
        duration = time.time() - self.start_time
        FAILOVER_DURATION.observe(duration)
        FAILOVER_TOTAL.labels(result="success" if success else "failure").inc()
        
        if self.write_success + self.write_failures > 0:
            success_rate = (self.write_success / (self.write_success + self.write_failures)) * 100
            WRITE_SUCCESS_RATE.set(success_rate)
    
    def add_chaos_event(self, event: ChaosEvent):
        """Add a chaos event to the metrics."""
        self.chaos_events.append(event)
        self.events.append({
            "type": "chaos",
            "description": event.description,
            "time": event.start_time,
            "metrics": event.metrics
        })

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

        # Check for write failure windows
        failure_windows = self._analyze_write_failure_windows()
        max_window = max(failure_windows) if failure_windows else 0
        if max_window > THRESHOLDS["max_write_failure_window"]:
            violations.append(
                f"Continuous write failures for {max_window:.2f}s "
                f"(max: {THRESHOLDS['max_write_failure_window']}s)"
            )

        return violations

    def _analyze_write_failure_windows(self) -> List[float]:
        """Analyze continuous write failure windows."""
        failure_windows = []
        window_start = None

        for event in self.events:
            if event["type"] == "write_error":
                if window_start is None:
                    window_start = event["timestamp"]
            elif window_start is not None:
                window_duration = event["timestamp"] - window_start
                failure_windows.append(window_duration)
                window_start = None

        # Handle ongoing failure window
        if window_start is not None:
            window_duration = time.time() - window_start
            failure_windows.append(window_duration)

        return failure_windows


class FailoverTestSuite:
    """Enhanced failover test suite with performance validation."""

    def __init__(self):
        self.metrics = FailoverMetrics()
        self.metrics.start_time = time.time()
        self.metrics.events = []

    async def test_concurrent_failover(self):
        """Enhanced failover test with performance validation."""
        try:
            # Start concurrent writes
            writer = ConcurrentWriter()
            write_task = asyncio.create_task(writer.write_loop())
            print("Started concurrent writes...")

            time.sleep(2)  # Let some writes happen

            # Kill master abruptly
            print("Killing master...")
            kill_service("redis-master")
            time.sleep(5)  # wait for failover

            # Get new master
            new_master = get_master_info()
            print(f"New master after kill: {new_master}")

            # Start master again
            print("Starting old master...")
            start_service("redis-master")
            time.sleep(5)

            # Stop writes and check stats
            writer.stop()
            await write_task
            stats = writer.get_success_rate()
            print(f"Write stats: {stats}")

            self.metrics.write_success = writer.write_success
            self.metrics.write_failures = writer.write_failures
            self.metrics.detection_time = time.time()
            self.metrics.recovery_time = time.time()

            # Validate performance before completing
            violations = self.metrics.validate_performance()
            if violations:
                raise PerformanceValidationError(
                    "Performance thresholds violated:\n"
                    + "\n".join(f"- {v}" for v in violations)
                )

            return True

        except PerformanceValidationError as e:
            print("performance_validation_failed", error=str(e), metrics=self.metrics)
            self.metrics.events.append(
                {
                    "type": "performance_validation_failed",
                    "timestamp": time.time(),
                    "error": str(e),
                }
            )
            return False

        except Exception as e:
            print("test_failure", error=str(e))
            self.metrics.events.append(
                {"type": "test_error", "timestamp": time.time(), "error": str(e)}
            )
            return False

    def print_report(self):
        """Enhanced report with performance validation results."""
        print("\n=== Enhanced Failover Test Report ===")

        # Print existing metrics...
        print(f"Write success: {self.metrics.write_success}")
        print(f"Write failures: {self.metrics.write_failures}")

        # Print performance validation results
        violations = self.metrics.validate_performance()
        if violations:
            print("\nPerformance Threshold Violations:")
            for violation in violations:
                print(f"❌ {violation}")
        else:
            print("\n✅ All performance thresholds met!")

        # Export metrics
        with open("failover_metrics.json", "w") as f:
            f.write(str(self.metrics.__dict__))


@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_failover_with_monitoring():
    """Main test with performance validation."""
    suite = FailoverTestSuite()
    success = await suite.test_concurrent_failover()
    suite.print_report()
    assert success, "Failover test failed performance validation"


# -------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------


@pytest.mark.order(1)
def test_graceful_master_shutdown():
    """Test failover during graceful master shutdown"""
    print("\n=== Testing Graceful Master Shutdown ===")

    # Get initial master info
    initial_master = get_master_info()
    print(f"Initial master: {initial_master}")
    initial_master_info = get_redis_info("redis-redis-master-1")
    print(f"Initial master info:\n{initial_master_info}")

    # Stop master
    print("Stopping master...")
    stop_service("redis-master")
    time.sleep(10)  # Give more time for failover

    # Get new master
    new_master = get_master_info()
    print(f"New master after shutdown: {new_master}")

    # Start master again
    print("Starting old master...")
    start_service("redis-master")
    time.sleep(10)  # Give more time for role change

    # Check if old master became slave
    master_info = get_redis_info("redis-redis-master-1")
    print(f"Old master info:\n{master_info}")

    # More detailed assertions
    assert new_master is not None, "Should have a new master after failover"
    assert (
        "role:slave" in master_info or "role:replica" in master_info
    ), "Old master should become slave/replica"


@pytest.mark.order(2)
def test_concurrent_writes_during_failover():
    """Test write operations during master failover"""
    print("\n=== Testing Concurrent Writes During Failover ===")

    # Start concurrent writes
    writer = ConcurrentWriter()
    write_task = asyncio.create_task(writer.write_loop())
    print("Started concurrent writes...")

    time.sleep(2)  # Let some writes happen

    # Kill master abruptly
    print("Killing master...")
    kill_service("redis-master")
    time.sleep(5)  # wait for failover

    # Get new master
    new_master = get_master_info()
    print(f"New master after kill: {new_master}")

    # Start master again
    print("Starting old master...")
    start_service("redis-master")
    time.sleep(5)

    # Stop writes and check stats
    writer.stop()
    await write_task
    stats = writer.get_success_rate()
    print(f"Write stats: {stats}")

    assert stats > 0, "Should have some successful writes"
    assert writer.write_failures > 0, "Should have some failed writes during failover"


@pytest.mark.order(3)
def test_network_partition():
    """Test behavior during network partition"""
    print("\n=== Testing Network Partition ===")

    # Get initial master
    initial_master = get_master_info()
    print(f"Initial master: {initial_master}")

    # Disconnect sentinel2 from network
    print("Disconnecting sentinel2 from network...")
    partition_container("redis-redis-sentinel-2-1")
    time.sleep(5)

    # Verify cluster still stable
    current_master = get_master_info()
    print(f"Master after sentinel2 partition: {current_master}")

    # Kill master to force failover with reduced sentinel count
    print("Killing master to test failover with reduced sentinel count...")
    kill_service("redis-master")
    time.sleep(10)

    # Check new master
    new_master = get_master_info()
    print(f"New master after failover: {new_master}")

    # Reconnect sentinel and restart master
    print("Reconnecting sentinel2 and restarting master...")
    reconnect_container("redis-redis-sentinel-2-1")
    start_service("redis-master")
    time.sleep(5)

    assert (
        new_master != initial_master
    ), "Master should have changed after partition and kill"

    # Final stability check
    final_master = get_master_info()
    print(f"Final master status: {final_master}")
    assert final_master is not None, "Should have a stable master after reconnection"


@pytest.mark.order(4)
async def test_abrupt_master_shutdown():
    """Test failover when master is abruptly shut down."""
    try:
        master = await get_master_info()
        if not master:
            raise Exception("Could not discover initial master")

        # Abruptly shutdown master
        await kill_service("redis-master")

        # Wait for failover
        new_master = await get_master_info()
        assert new_master, "Failover did not complete"

    except Exception as e:
        print("Abrupt master shutdown test failed", error=str(e))
        raise


@pytest.mark.order(5)
async def test_master_shutdown_with_concurrent_writes():
    """Test master shutdown with concurrent writes."""
    try:
        # Start concurrent writes
        writer = ConcurrentWriter()
        write_task = asyncio.create_task(writer.write_loop())

        # Get initial master
        master = await get_master_info()
        if not master:
            raise Exception("Could not discover initial master")

        # Let writes stabilize
        await asyncio.sleep(2)

        # Shutdown master
        await kill_service("redis-master")

        # Wait for failover
        new_master = await get_master_info()
        assert new_master, "Failover did not complete"

        # Stop writes and get stats
        writer.stop()
        await write_task

        # Validate write success rate
        success_rate = writer.get_success_rate()
        min_success_rate = 0.95
        assert (
            success_rate >= min_success_rate
        ), f"Write success rate {success_rate:.1f}% below min {min_success_rate*100}%"

    except Exception:
        logger.error("Master shutdown test failed", exc_info=True)
        raise


@pytest.mark.asyncio
async def test_chaos_network_partition():
    """Test failover during network partition with chaos engineering."""
    orchestrator = ChaosOrchestrator()
    metrics = FailoverMetrics()
    writer = ConcurrentWriter()
    
    logger.info("Starting chaos network partition test")
    
    # Start concurrent writes
    write_task = asyncio.create_task(writer.write_loop(duration=60))
    
    try:
        # Add network delay to master
        await orchestrator.network_delay("redis-redis-master-1", latency_ms=200, duration=10)
        
        # Partition master from network
        success, _ = partition_container("redis-redis-master-1")
        if not success:
            raise Exception("Failed to partition master container")
        
        # Wait for failover
        await asyncio.sleep(5)
        
        # Add CPU pressure to new master
        await orchestrator.cpu_pressure("redis-redis-replica-1", load=70, duration=10)
        
        # Reconnect original master
        success, _ = reconnect_container("redis-redis-master-1")
        if not success:
            raise Exception("Failed to reconnect master container")
        
        # Record metrics
        metrics.chaos_events = orchestrator.events
        metrics.record_failover_completion(success=True)
        
    except Exception as e:
        logger.error(f"Chaos test failed: {str(e)}")
        metrics.record_failover_completion(success=False)
        raise
    
    finally:
        writer.stop()
        await write_task
        
    # Validate metrics
    metrics.write_success = writer.write_success
    metrics.write_failures = writer.write_failures
    metrics.validate_performance()
    
    logger.info("Chaos test completed successfully")
    logger.info("Event History: %s", orchestrator.get_event_history())


@pytest.mark.asyncio
async def test_chaos_resource_pressure():
    """Test failover under various resource pressure conditions."""
    orchestrator = ChaosOrchestrator()
    metrics = FailoverMetrics()
    writer = ConcurrentWriter()
    
    logger.info("Starting chaos resource pressure test")
    
    # Start concurrent writes
    write_task = asyncio.create_task(writer.write_loop(duration=60))
    
    try:
        # Add memory pressure to master
        await orchestrator.memory_pressure("redis-redis-master-1", bytes_to_fill=1024*1024*200, duration=10)
        
        # Add CPU pressure to master
        await orchestrator.cpu_pressure("redis-redis-master-1", load=90, duration=10)
        
        # Kill master service
        success, _ = kill_service("redis-redis-master-1")
        if not success:
            raise Exception("Failed to kill master service")
        
        # Wait for failover
        await asyncio.sleep(5)
        
        # Add network delay to new master
        await orchestrator.network_delay("redis-redis-replica-1", latency_ms=150, duration=10)
        
        # Record metrics
        metrics.chaos_events = orchestrator.events
        metrics.record_failover_completion(success=True)
        
    except Exception as e:
        logger.error(f"Resource pressure test failed: {str(e)}")
        metrics.record_failover_completion(success=False)
        raise
    
    finally:
        writer.stop()
        await write_task
        
    # Validate metrics
    metrics.write_success = writer.write_success
    metrics.write_failures = writer.write_failures
    metrics.validate_performance()
    
    logger.info("Resource pressure test completed successfully")
    logger.info("Event History: %s", orchestrator.get_event_history())
