# Redis Sentinel High Availability Cluster

## Architecture Overview
The Redis cluster consists of:
- 1 Redis master
- 2 Redis replicas
- 3 Sentinel nodes
All components run in Docker containers on a custom network.

## Network Configuration
```
Network: redis_redis-net
Subnet: 172.19.0.0/16

Container IPs:
- Redis Master: 172.19.0.2
- Redis Replica 1: 172.19.0.3
- Redis Replica 2: 172.19.0.4
- Sentinel 1: 172.19.0.5
- Sentinel 2: 172.19.0.6
- Sentinel 3: 172.19.0.7
```

## Component Configuration

### Redis Master
- Port: 6379
- Configuration: `/redis/master/redis.conf`
- Data persistence: RDB + AOF
- Memory limit: 2GB

### Redis Replicas
- Ports: 6380, 6381
- Configuration: `/redis/replica/redis.conf`
- Replication strategy: Disk-backed
- Read-only mode: Enabled

### Sentinel Nodes
- Ports: 26379-26381
- Configuration: `/redis/sentinel/sentinel.conf`
- Quorum: 2
- Failover timeout: 30000ms

## High Availability Features

### Automatic Failover
1. Triggered when master is unreachable
2. Requires quorum of 2 sentinels
3. Promotes most up-to-date replica
4. Updates configuration files automatically

### Monitoring
- Integrated with Prometheus + Grafana
- Key metrics tracked:
  * Memory usage
  * Replication lag
  * Failover events
  * Command throughput
  * Network I/O

## Deployment

### Starting the Cluster
```bash
cd redis
docker compose up -d
```

### Verifying Health
```bash
# Check sentinel status
docker exec -it redis-sentinel-1 redis-cli -p 26379 info sentinel

# Check replication status
docker exec -it redis-master redis-cli info replication
```

## Maintenance

### Adding New Replica
1. Add configuration to docker-compose.yml
2. Update network settings
3. Start new container
4. Verify replication status

### Scaling Sentinels
1. Add new sentinel configuration
2. Update quorum if needed
3. Start new sentinel container
4. Verify sentinel discovery

### Backup Strategy
1. Automatic RDB snapshots every 1 hour
2. AOF persistence enabled
3. Backup files stored in `/redis/backup`
4. Replicas maintain their own backups

## Troubleshooting

### Common Issues

1. Split-Brain Prevention
   - Quorum requirement prevents split-brain
   - Minimum 2 sentinels must agree
   - Automatic replica consistency check

2. Network Partition Handling
   - Sentinels monitor network connectivity
   - Automatic failback when partition heals
   - Configurable timeout settings

3. Data Consistency
   - WAIT command for synchronous replication
   - Configurable min-replicas-to-write
   - Automatic full resync when needed

### Health Checks
```bash
# Check sentinel status
redis-cli -p 26379 sentinel master mymaster

# Check replication lag
redis-cli -p 6379 info replication

# Monitor failover events
redis-cli -p 26379 sentinel events
```

## Security

### Network Security
- Custom Docker network
- Fixed IP addresses
- Limited port exposure

### Access Control
- Protected mode enabled
- Password authentication
- ACL configuration

## Performance Tuning

### Memory Management
- maxmemory: 2GB
- maxmemory-policy: volatile-lru
- Lazy freeing enabled

### Persistence Settings
- RDB snapshot interval: 3600 seconds
- AOF fsync: everysec
- AOF rewrite threshold: 100%

## Monitoring Integration

### Prometheus Metrics
- Redis Exporter (9121)
- Sentinel Exporter (9122)
- Custom recording rules
- Alert thresholds

### Grafana Dashboard
- Real-time metrics
- Historical trends
- Alert visualization
- Performance analytics

## Recovery Procedures

### Manual Failover
```bash
# Trigger manual failover
redis-cli -p 26379 sentinel failover mymaster
```

### Data Recovery
1. Stop affected instance
2. Copy RDB/AOF from healthy replica
3. Restart instance
4. Verify replication status

## Future Enhancements
1. Implement Redis Cluster for sharding
2. Add SSL/TLS encryption
3. Enhance backup automation
4. Implement cross-datacenter replication
