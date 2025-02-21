# Redis Sentinel Security Configuration

## Overview

This document describes the secure Redis Sentinel setup for our authentication system, including configuration details, security measures, and monitoring tools.

## Architecture

- **Master Node**: Primary Redis instance (port 6379)
- **Replica Node**: Secondary Redis instance (port 6380)
- **Sentinel Node**: Monitoring and failover management (port 26379)

## Security Measures

### Password Authentication
- All nodes (master, replica, sentinel) require password authentication
- Passwords are managed via environment variables
- Sentinel is configured with auth-pass for master communication

### Network Security
- All nodes run in an isolated Docker network (redis-net)
- Protected mode can be enabled in production
- Port exposure is configurable via environment variables

## Configuration Files

### Docker Compose (docker-compose.redis-ha.yml)
```yaml
services:
  redis-master:
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}

  redis-replica:
    command: [
      "redis-server",
      "--requirepass", "${REDIS_PASSWORD}",
      "--masterauth", "${REDIS_PASSWORD}"
    ]

  sentinel:
    command: ["redis-server", "/etc/redis/sentinel.conf", "--sentinel"]
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
```

### Sentinel Configuration (sentinel.conf)
```conf
sentinel monitor mymaster redis-master 6379 ${REDIS_SENTINEL_QUORUM}
sentinel auth-pass mymaster ${REDIS_PASSWORD}
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
```

## Environment Variables

Required environment variables in `.env`:
```bash
REDIS_PASSWORD=<secure_password>
REDIS_MASTER_NAME=mymaster
REDIS_MASTER_PORT=6379
REDIS_REPLICA_1_PORT=6380
REDIS_SENTINEL_1_PORT=26379
REDIS_SENTINEL_QUORUM=2
```

## Testing and Monitoring

### Security Testing
Run the security test suite:
```bash
python server/tests/core/test_redis_security.py
```

This will verify:
- Password authentication on all nodes
- Proper master-replica replication
- Sentinel authentication and master discovery

### Continuous Monitoring
Start the monitoring script:
```bash
python server/core/monitor_redis_cluster.py
```

Features:
- Real-time health checks of all nodes
- Authentication verification
- Replication status monitoring
- Sentinel state verification

## Troubleshooting

### Common Issues

1. Authentication Errors
   - Verify REDIS_PASSWORD is set correctly in environment
   - Check sentinel.conf contains correct auth-pass
   - Ensure master and replica share the same password

2. Replication Issues
   - Check replica logs for connection errors
   - Verify masterauth configuration
   - Monitor replication lag

3. Sentinel Issues
   - Verify quorum settings match number of sentinels
   - Check sentinel authentication
   - Monitor sentinel logs for auth failures

### Useful Commands

Check master status:
```bash
redis-cli -p 6379 -a "$REDIS_PASSWORD" info replication
```

Check replica status:
```bash
redis-cli -p 6380 -a "$REDIS_PASSWORD" info replication
```

Check sentinel status:
```bash
redis-cli -p 26379 sentinel master mymaster
```

## Production Considerations

1. Security
   - Enable protected mode
   - Use strong passwords
   - Implement network security (firewall rules, VPC)
   - Regular security audits

2. High Availability
   - Deploy multiple sentinel nodes
   - Adjust quorum based on sentinel count
   - Monitor failover events
   - Regular backup strategy

3. Monitoring
   - Integration with monitoring systems (Prometheus/Grafana)
   - Alert configuration for critical events
   - Performance metrics collection
   - Log aggregation

## Next Steps

1. Scale Out
   - Add additional sentinel nodes
   - Deploy more replicas
   - Adjust quorum settings

2. Monitoring Enhancement
   - Set up Prometheus metrics
   - Configure Grafana dashboards
   - Implement alerting

3. Security Hardening
   - Enable TLS encryption
   - Implement role-based access
   - Regular security assessments
