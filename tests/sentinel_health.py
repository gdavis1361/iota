"""Redis Sentinel health check utilities."""
import logging
import asyncio
import redis.asyncio as redis
from typing import List, Dict, Optional, Tuple
from prometheus_client import Gauge, Counter, Histogram

# Metrics
sentinel_health = Gauge('redis_sentinel_health', 'Health status of Redis Sentinel nodes', ['node'])
sentinel_quorum = Gauge('redis_sentinel_quorum_size', 'Current size of the Sentinel quorum')
sentinel_master_health = Gauge('redis_master_health', 'Health status of Redis master')
sentinel_replica_health = Gauge('redis_replica_health', 'Health status of Redis replicas', ['replica'])
sentinel_failover_count = Counter('redis_sentinel_failover_total', 'Total number of failovers triggered')
sentinel_response_time = Histogram('redis_sentinel_response_seconds', 'Response time for Sentinel operations')

logger = logging.getLogger(__name__)

class SentinelHealthCheck:
    """Health check implementation for Redis Sentinel cluster."""
    
    def __init__(self, sentinel_hosts: List[str], sentinel_port: int = 26379):
        self.sentinel_hosts = sentinel_hosts
        self.sentinel_port = sentinel_port
        self.logger = logging.getLogger(f"{__name__}.health_check")
        
    async def check_sentinel_quorum(self, master_name: str = "mymaster") -> Tuple[bool, Dict]:
        """Verify Sentinel quorum and master/replica status."""
        results = {}
        healthy_sentinels = 0
        
        for host in self.sentinel_hosts:
            try:
                sentinel = redis.Redis(
                    host=host,
                    port=self.sentinel_port,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                    decode_responses=True
                )
                
                # Check sentinel status
                start_time = asyncio.get_event_loop().time()
                await sentinel.ping()
                response_time = asyncio.get_event_loop().time() - start_time
                sentinel_response_time.observe(response_time)
                
                # Get master status
                master_info = await sentinel.execute_command('SENTINEL', 'master', master_name)
                if not master_info:
                    raise Exception(f"No master info returned for {master_name}")
                
                # Get replica status
                replicas = await sentinel.execute_command('SENTINEL', 'replicas', master_name)
                
                # Update metrics
                sentinel_health.labels(node=host).set(1)
                healthy_sentinels += 1
                
                results[host] = {
                    'status': 'healthy',
                    'master_info': master_info,
                    'replica_count': len(replicas),
                    'response_time': response_time
                }
                
                self.logger.info(f"Sentinel {host} is healthy. Master: {master_info[3]}:{master_info[5]}, Replicas: {len(replicas)}")
                
            except Exception as e:
                sentinel_health.labels(node=host).set(0)
                results[host] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                self.logger.error(f"Sentinel {host} health check failed: {e}")
            finally:
                await sentinel.close()
        
        # Update quorum metrics
        sentinel_quorum.set(healthy_sentinels)
        
        # Quorum is considered healthy if majority of sentinels are up
        quorum_healthy = healthy_sentinels > len(self.sentinel_hosts) // 2
        if not quorum_healthy:
            self.logger.error(f"Sentinel quorum unhealthy. Only {healthy_sentinels}/{len(self.sentinel_hosts)} sentinels available")
        
        return quorum_healthy, results
    
    async def verify_master_status(self, master_host: str, master_port: int) -> bool:
        """Verify Redis master is responsive and has expected role."""
        try:
            master = redis.Redis(
                host=master_host,
                port=master_port,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                decode_responses=True
            )
            
            # Check basic connectivity
            start_time = asyncio.get_event_loop().time()
            await master.ping()
            response_time = asyncio.get_event_loop().time() - start_time
            
            # Verify role
            role_info = await master.execute_command('ROLE')
            is_master = role_info[0] == 'master'
            
            if is_master:
                sentinel_master_health.set(1)
                self.logger.info(f"Master {master_host}:{master_port} is healthy. Response time: {response_time:.3f}s")
            else:
                sentinel_master_health.set(0)
                self.logger.error(f"Node {master_host}:{master_port} is not in master role")
            
            await master.close()
            return is_master
            
        except Exception as e:
            sentinel_master_health.set(0)
            self.logger.error(f"Master health check failed for {master_host}:{master_port}: {e}")
            return False
    
    async def verify_replica_status(self, replica_host: str, replica_port: int) -> bool:
        """Verify Redis replica is responsive and properly replicating."""
        try:
            replica = redis.Redis(
                host=replica_host,
                port=replica_port,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                decode_responses=True
            )
            
            # Check basic connectivity
            await replica.ping()
            
            # Verify role and replication status
            role_info = await replica.execute_command('ROLE')
            is_replica = role_info[0] == 'slave'
            is_connected = role_info[3] == 'connected'
            
            status = is_replica and is_connected
            sentinel_replica_health.labels(replica=f"{replica_host}:{replica_port}").set(1 if status else 0)
            
            if status:
                self.logger.info(f"Replica {replica_host}:{replica_port} is healthy and replicating")
            else:
                self.logger.error(f"Replica {replica_host}:{replica_port} status check failed. Role: {role_info[0]}, State: {role_info[3]}")
            
            await replica.close()
            return status
            
        except Exception as e:
            sentinel_replica_health.labels(replica=f"{replica_host}:{replica_port}").set(0)
            self.logger.error(f"Replica health check failed for {replica_host}:{replica_port}: {e}")
            return False
