import pytest
import asyncio
import time
import logging
import redis.asyncio as redis
from dataclasses import dataclass
from typing import List, Dict, Optional
from prometheus_client import Counter, Histogram, Gauge
import subprocess
import json
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential
from sentinel_health import SentinelHealthCheck

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chaos_tests.log')
    ]
)
logger = logging.getLogger(__name__)

# Test metrics
write_success = Counter('test_write_success_total', 'Number of successful write operations')
write_failure = Counter('test_write_failure_total', 'Number of failed write operations')
operation_latency = Histogram('test_operation_latency_seconds', 'Latency of Redis operations')
connection_attempts = Counter('test_connection_attempts_total', 'Number of connection attempts')
connection_failures = Counter('test_connection_failures_total', 'Number of connection failures')

@dataclass
class FailoverMetrics:
    """Metrics for failover testing"""
    write_success_rate: float = 0.0
    detection_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'write_success_rate': self.write_success_rate,
            'detection_time': self.detection_time
        }

class CircuitBreaker:
    """Circuit breaker for Redis operations"""
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.is_open = False
        self.logger = logging.getLogger(f"{__name__}.circuit_breaker")
    
    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        current_time = time.time()
        if current_time - self.last_failure_time > self.reset_timeout:
            self.failure_count = 0
        
        self.failure_count += 1
        self.last_failure_time = current_time
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            self.logger.warning("Circuit breaker opened due to multiple failures")
    
    def record_success(self):
        """Record a success and potentially close the circuit"""
        self.failure_count = 0
        self.is_open = False
    
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if not self.is_open:
            return True
        
        if time.time() - self.last_failure_time > self.reset_timeout:
            self.logger.info("Circuit breaker reset timeout reached, allowing retry")
            self.is_open = False
            self.failure_count = 0
            return True
            
        return False

class RedisClient:
    """Redis client with retry and circuit breaker capabilities"""
    def __init__(self, host: str = "redis-master", port: int = 6379):
        self.host = host
        self.port = port
        self.client = None
        self.circuit_breaker = CircuitBreaker()
        self.logger = logging.getLogger(f"redis.client.{host}:{port}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def connect(self):
        """Connect to Redis with retry logic and circuit breaker"""
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is open")
            
        try:
            connection_attempts.inc()
            self.logger.info(f"Attempting connection to Redis at {self.host}:{self.port}")
            
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                socket_timeout=10.0,  # Increased timeout
                socket_connect_timeout=10.0,  # Increased timeout
                retry_on_timeout=True,
                decode_responses=True
            )
            
            # Test the connection
            start_time = time.time()
            await self.client.ping()
            latency = time.time() - start_time
            operation_latency.observe(latency)
            
            self.logger.info(f"Successfully connected to Redis. Latency: {latency:.3f}s")
            self.circuit_breaker.record_success()
            return self.client
            
        except Exception as e:
            connection_failures.inc()
            self.circuit_breaker.record_failure()
            self.logger.error(f"Unexpected error during connection: {str(e)}")
            if self.client:
                await self.client.close()
            raise

    async def close(self):
        """Close the Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=4),
        reraise=True
    )
    async def write_data(self, key: str, value: str) -> bool:
        """Write data to Redis with retry logic"""
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is open")
            
        if not self.client:
            raise RuntimeError("Redis client not connected")
            
        try:
            start_time = time.time()
            await self.client.set(key, value)
            latency = time.time() - start_time
            operation_latency.observe(latency)
            
            write_success.inc()
            self.circuit_breaker.record_success()
            return True
            
        except Exception as e:
            write_failure.inc()
            self.circuit_breaker.record_failure()
            self.logger.error(f"Error writing data: {str(e)}")
            raise

@pytest.fixture(scope="session")
async def sentinel_health():
    """Fixture to provide sentinel health checking"""
    return SentinelHealthCheck(
        sentinel_hosts=["redis-sentinel-1", "redis-sentinel-2", "redis-sentinel-3"]
    )

@pytest.fixture(scope="function")
async def verify_sentinel_health(sentinel_health):
    """Fixture to verify sentinel health before each test"""
    logger.info("Verifying Sentinel cluster health before test")
    healthy, results = await sentinel_health.check_sentinel_quorum()
    
    if not healthy:
        pytest.skip("Sentinel cluster is not healthy")
    
    # Verify master health
    master_healthy = await sentinel_health.verify_master_status("redis-master", 6379)
    if not master_healthy:
        pytest.skip("Redis master is not healthy")
    
    # Verify replica health
    replica1_healthy = await sentinel_health.verify_replica_status("redis-replica-1", 6379)
    replica2_healthy = await sentinel_health.verify_replica_status("redis-replica-2", 6379)
    if not (replica1_healthy and replica2_healthy):
        pytest.skip("Redis replicas are not healthy")
    
    logger.info("Sentinel cluster health verification passed")

@pytest.fixture(scope="function")
async def redis_client(verify_sentinel_health):
    """Fixture to provide a Redis client with proper cleanup"""
    client = RedisClient(host="redis-master", port=6379)
    try:
        await client.connect()
        return client
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        await client.close()
        raise

@pytest.fixture(scope="function")
async def chaos_orchestrator():
    """Fixture to provide a chaos orchestrator with cleanup"""
    try:
        orchestrator = ChaosOrchestrator("redis-master")
        return orchestrator
    except Exception as e:
        logger.error(f"Failed to create chaos orchestrator: {e}")
        raise

async def perform_writes(client: RedisClient, count: int = 100) -> FailoverMetrics:
    """Perform a series of writes and track metrics"""
    metrics = FailoverMetrics()
    start_time = time.time()
    success_count = 0
    
    try:
        for i in range(count):
            try:
                key = f"test_key_{i}"
                value = f"test_value_{i}"
                if await client.write_data(key, value):
                    success_count += 1
                await asyncio.sleep(0.1)  # Small delay between writes
            except Exception as e:
                logger.error(f"Write failed for iteration {i}: {e}")
                write_failure.inc()
                continue
            
            write_success.inc()
            
        metrics.write_success_rate = success_count / count
        metrics.detection_time = time.time() - start_time
        return metrics
        
    except Exception as e:
        logger.error(f"Error during write performance test: {e}")
        metrics.write_success_rate = success_count / count if count > 0 else 0
        metrics.detection_time = time.time() - start_time
        return metrics

@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_network_delay_failover(redis_client, chaos_orchestrator):
    """Test failover behavior with network delay"""
    # Await the fixtures
    client = await redis_client
    orchestrator = await chaos_orchestrator
    
    logger.info("Starting network delay failover test")
    metrics = FailoverMetrics()
    
    try:
        # Baseline writes
        logger.info("Performing baseline writes")
        baseline_metrics = await perform_writes(client, count=50)
        assert baseline_metrics.write_success_rate > 0.95, "Baseline writes should have high success rate"
        
        # Inject network delay
        logger.info("Injecting network delay")
        await orchestrator.inject_network_delay(delay_ms=200)
        await asyncio.sleep(2)  # Allow delay to take effect
        
        # Perform writes under network delay
        logger.info("Performing writes under network delay")
        chaos_metrics = await perform_writes(client, count=50)
        
        # Validate metrics
        assert chaos_metrics.write_success_rate > 0.8, "Write success rate should remain reasonable under delay"
        assert chaos_metrics.detection_time < 5.0, "Failover detection should be quick"
        
        # Record metrics
        metrics.write_success_rate = chaos_metrics.write_success_rate
        metrics.detection_time = chaos_metrics.detection_time
        logger.info(f"Test metrics: {metrics.to_dict()}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        logger.info("Cleaning up network delay test")
        await orchestrator.restore_normal_conditions()
        await client.close()

@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_cpu_pressure_failover(redis_client, chaos_orchestrator):
    """Test failover behavior under CPU pressure"""
    # Await the fixtures
    client = await redis_client
    orchestrator = await chaos_orchestrator
    
    logger.info("Starting CPU pressure failover test")
    metrics = FailoverMetrics()
    
    try:
        # Baseline writes
        logger.info("Performing baseline writes")
        baseline_metrics = await perform_writes(client, count=50)
        assert baseline_metrics.write_success_rate > 0.95, "Baseline writes should have high success rate"
        
        # Inject CPU pressure
        logger.info("Injecting CPU pressure")
        await orchestrator.inject_cpu_pressure(cpu_load=80)
        await asyncio.sleep(2)  # Allow pressure to take effect
        
        # Perform writes under CPU pressure
        logger.info("Performing writes under CPU pressure")
        chaos_metrics = await perform_writes(client, count=50)
        
        # Validate metrics
        assert chaos_metrics.write_success_rate > 0.8, "Write success rate should remain reasonable under CPU pressure"
        assert chaos_metrics.detection_time < 5.0, "Operations should complete within timeout"
        
        # Record metrics
        metrics.write_success_rate = chaos_metrics.write_success_rate
        metrics.detection_time = chaos_metrics.detection_time
        logger.info(f"Test metrics: {metrics.to_dict()}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        logger.info("Cleaning up CPU pressure test")
        await orchestrator.restore_normal_conditions()
        await client.close()

@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_memory_pressure_failover(redis_client, chaos_orchestrator):
    """Test failover behavior under memory pressure"""
    # Await the fixtures
    client = await redis_client
    orchestrator = await chaos_orchestrator
    
    logger.info("Starting memory pressure failover test")
    metrics = FailoverMetrics()
    
    try:
        # Baseline writes
        logger.info("Performing baseline writes")
        baseline_metrics = await perform_writes(client, count=50)
        assert baseline_metrics.write_success_rate > 0.95, "Baseline writes should have high success rate"
        
        # Inject memory pressure
        logger.info("Injecting memory pressure")
        await orchestrator.inject_memory_pressure(memory_bytes=256*1024*1024)  # 256MB
        await asyncio.sleep(2)  # Allow pressure to take effect
        
        # Perform writes under memory pressure
        logger.info("Performing writes under memory pressure")
        chaos_metrics = await perform_writes(client, count=50)
        
        # Validate metrics
        assert chaos_metrics.write_success_rate > 0.8, "Write success rate should remain reasonable under memory pressure"
        assert chaos_metrics.detection_time < 5.0, "Operations should complete within timeout"
        
        # Record metrics
        metrics.write_success_rate = chaos_metrics.write_success_rate
        metrics.detection_time = chaos_metrics.detection_time
        logger.info(f"Test metrics: {metrics.to_dict()}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        logger.info("Cleaning up memory pressure test")
        await orchestrator.restore_normal_conditions()
        await client.close()

@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_combined_pressure_failover(redis_client, chaos_orchestrator):
    """Test failover behavior under combined system pressure"""
    # Await the fixtures
    client = await redis_client
    orchestrator = await chaos_orchestrator
    
    logger.info("Starting combined pressure failover test")
    metrics = FailoverMetrics()
    
    try:
        # Baseline writes
        logger.info("Performing baseline writes")
        baseline_metrics = await perform_writes(client, count=50)
        assert baseline_metrics.write_success_rate > 0.95, "Baseline writes should have high success rate"
        
        # Inject combined pressure
        logger.info("Injecting combined pressure")
        await orchestrator.inject_network_delay(delay_ms=100)
        await orchestrator.inject_cpu_pressure(cpu_load=60)
        await orchestrator.inject_memory_pressure(memory_bytes=128*1024*1024)  # 128MB
        await asyncio.sleep(3)  # Allow pressures to take effect
        
        # Perform writes under combined pressure
        logger.info("Performing writes under combined pressure")
        chaos_metrics = await perform_writes(client, count=50)
        
        # Validate metrics
        assert chaos_metrics.write_success_rate > 0.7, "Write success rate should remain acceptable under combined pressure"
        assert chaos_metrics.detection_time < 8.0, "Operations should complete within extended timeout"
        
        # Record metrics
        metrics.write_success_rate = chaos_metrics.write_success_rate
        metrics.detection_time = chaos_metrics.detection_time
        logger.info(f"Test metrics: {metrics.to_dict()}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        logger.info("Cleaning up combined pressure test")
        await orchestrator.restore_normal_conditions()
        await client.close()

class ChaosOrchestrator:
    def __init__(self, container_name: str):
        self.container_name = container_name
        self.logger = logging.getLogger(f"chaos.{container_name}")
        self.active_chaos = set()
        
    async def inject_network_delay(self, delay_ms: int = 100):
        """Add network latency to container"""
        self.logger.info(f"Injecting {delay_ms}ms network delay into {self.container_name}")
        cmd = f"tc qdisc add dev eth0 root netem delay {delay_ms}ms"
        await self._run_command(cmd)
        self.active_chaos.add("network_delay")
        
    async def inject_cpu_pressure(self, cpu_load: int = 80):
        """Generate CPU load in container"""
        self.logger.info(f"Injecting {cpu_load}% CPU pressure into {self.container_name}")
        cmd = f"stress-ng --cpu 1 --cpu-load {cpu_load} &"
        await self._run_command(cmd)
        self.active_chaos.add("cpu_pressure")
        
    async def inject_memory_pressure(self, memory_bytes: int = 512*1024*1024):
        """Consume memory in container"""
        memory_mb = memory_bytes // (1024*1024)
        self.logger.info(f"Injecting {memory_mb}MB memory pressure into {self.container_name}")
        cmd = f"stress-ng --vm 1 --vm-bytes {memory_bytes}B &"
        await self._run_command(cmd)
        self.active_chaos.add("memory_pressure")
        
    async def restore_normal_conditions(self):
        """Clean up chaos conditions with logging"""
        self.logger.info(f"Restoring normal conditions in {self.container_name}")
        cleanup_commands = {
            "network_delay": "tc qdisc del dev eth0 root",
            "cpu_pressure": "pkill -f stress-ng",
            "memory_pressure": "pkill -f stress-ng"
        }
        
        for chaos_type in self.active_chaos:
            if chaos_type in cleanup_commands:
                try:
                    await self._run_command(cleanup_commands[chaos_type])
                    self.logger.info(f"Cleaned up {chaos_type}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up {chaos_type}: {e}")
        
        self.active_chaos.clear()
        
    async def _run_command(self, cmd: str) -> str:
        """Run command in container with proper error handling and logging"""
        try:
            self.logger.debug(f"Running command in {self.container_name}: {cmd}")
            result = subprocess.run(
                ["docker", "exec", self.container_name, "sh", "-c", cmd],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.debug(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e.stderr}")
            raise
