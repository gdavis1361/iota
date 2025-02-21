# Redis Network Partition Testing

This module contains comprehensive tests for validating Redis Sentinel behavior under various network partition scenarios.

## Test Scenarios

1. **Sentinel Partition from Master**
   - Disconnects one sentinel from the master
   - Verifies no failover occurs when other sentinels can still see the master
   - Tests sentinel quorum behavior

2. **Master Partition from All Sentinels**
   - Isolates master from all sentinels
   - Verifies proper failover to replica
   - Tests failover timing and consistency

3. **Replica Partition from Master**
   - Disconnects replica from master
   - Verifies no unnecessary failover occurs
   - Tests replication recovery

4. **Split-Brain Prevention**
   - Creates network partition between sentinels
   - Verifies no failover occurs without proper quorum
   - Tests cluster stability under network splits

## Running Tests

```bash
# Run all partition tests
cd server/tests/redis
python -m pytest network_partition/test_redis_partition.py -v

# Run specific test
python -m pytest network_partition/test_redis_partition.py -v -k "test_master_partition"
```

## Test Configuration

- Sentinel Quorum: 2 (majority of 3 sentinels)
- Failover Timeout: 30000ms
- Down-after-milliseconds: 3000ms

## Dependencies

- Python 3.x
- pytest
- docker-py
- redis-py

## Notes

1. Tests require Docker daemon access
2. Redis cluster must be running via docker-compose
3. Network operations may require elevated privileges
4. Tests automatically clean up network changes

## Logging

Tests use Python's logging module with INFO level to track:
- Network partition events
- Master changes
- Failover timing
- Error conditions

## Future Enhancements

1. Add concurrent write tests during partitions
2. Implement network latency simulation
3. Add metrics collection for failover timing
4. Expand split-brain scenarios
