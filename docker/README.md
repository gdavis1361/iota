# Docker Configuration Documentation

## Project Structure
```
docker/
├── redis/
│   ├── master/
│   │   ├── Dockerfile
│   │   └── redis.conf
│   ├── replica/
│   │   ├── Dockerfile
│   │   └── redis.conf
│   └── sentinel/
│       ├── Dockerfile
│       └── sentinel.conf
├── monitoring/
│   ├── grafana/
│   │   └── Dockerfile
│   └── prometheus/
│       └── Dockerfile
└── server/
    └── Dockerfile
```

## Docker Networks

### Redis Network
```yaml
networks:
  redis-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.19.0.0/16
```
- Used by Redis master, replicas, and sentinels
- Fixed IP addressing for reliable service discovery
- Isolated network for security

### Monitoring Network
```yaml
networks:
  monitoring:
    driver: bridge
```
- Used by Prometheus, Grafana, and exporters
- Allows metric collection from Redis containers
- Separate from application traffic

## Docker Compose Files

### 1. Redis Stack (docker-compose.yml)
```yaml
version: '3.8'
services:
  redis-master:
    build: ./docker/redis/master
    networks:
      redis-net:
        ipv4_address: 172.19.0.2
    volumes:
      - redis_master_data:/data

  redis-replica-1:
    build: ./docker/redis/replica
    networks:
      redis-net:
        ipv4_address: 172.19.0.3
    volumes:
      - redis_replica1_data:/data

  redis-sentinel-1:
    build: ./docker/redis/sentinel
    networks:
      redis-net:
        ipv4_address: 172.19.0.5
```

### 2. Monitoring Stack (docker-compose.monitoring.yml)
```yaml
version: '3.8'
services:
  prometheus:
    build: ./docker/monitoring/prometheus
    volumes:
      - prometheus_data:/prometheus
      - ./prometheus/rules:/etc/prometheus/rules

  grafana:
    build: ./docker/monitoring/grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
```

## Volume Management

### Persistent Volumes
```yaml
volumes:
  redis_master_data:
  redis_replica1_data:
  redis_replica2_data:
  prometheus_data:
  grafana_data:
```
- Data persistence across container restarts
- Backup-friendly volume naming
- Separate volumes for each service

## Resource Management

### Memory Limits
```yaml
services:
  redis-master:
    mem_limit: 2g
    mem_reservation: 1g

  prometheus:
    mem_limit: 1g
    mem_reservation: 512m

  grafana:
    mem_limit: 512m
    mem_reservation: 256m
```

### CPU Limits
```yaml
services:
  redis-master:
    cpus: 2
  prometheus:
    cpus: 1
  grafana:
    cpus: 0.5
```

## Health Checks

### Redis Services
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 3
  start_period: 10s
```

### Monitoring Services
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000"]
  interval: 10s
  timeout: 5s
  retries: 3
```

## Deployment Commands

### Starting Services
```bash
# Start Redis stack
docker compose up -d

# Start monitoring stack
docker compose -f docker-compose.monitoring.yml up -d
```

### Scaling Services
```bash
# Scale Redis replicas
docker compose up -d --scale redis-replica=3

# Scale Sentinel nodes
docker compose up -d --scale redis-sentinel=3
```

### Maintenance
```bash
# View logs
docker compose logs -f [service_name]

# Check container health
docker compose ps

# Restart service
docker compose restart [service_name]
```

## Security Considerations

### Network Security
- Use of custom networks with fixed IPs
- Minimal port exposure
- Container isolation

### Access Control
- No root container processes
- Volume mount permissions
- Environment variable management

### Image Security
- Multi-stage builds
- Minimal base images
- Regular security updates

## Backup Strategy

### Volume Backups
```bash
# Create volume backup
docker run --rm -v redis_master_data:/data -v /backup:/backup \
    alpine tar czf /backup/redis_master_$(date +%Y%m%d).tar.gz /data
```

### Configuration Backups
- Regular backup of docker-compose files
- Version control for Dockerfiles
- Documentation of custom configurations

## Troubleshooting

### Common Issues
1. Container startup failures
   - Check logs: `docker compose logs [service]`
   - Verify configurations
   - Check resource limits

2. Network connectivity
   - Inspect networks: `docker network inspect`
   - Check container DNS
   - Verify IP assignments

3. Volume permissions
   - Check mount points
   - Verify ownership
   - Review access rights

## Best Practices

1. Container Management
   - Use specific version tags
   - Implement health checks
   - Set resource limits
   - Regular image updates

2. Network Configuration
   - Use custom networks
   - Implement fixed IPs
   - Minimal port exposure

3. Volume Management
   - Use named volumes
   - Regular backups
   - Clear mounting points

4. Monitoring
   - Container health checks
   - Resource monitoring
   - Log aggregation

## Future Improvements
1. Implement Docker Swarm or Kubernetes
2. Add container logging to ELK stack
3. Implement automated backup solution
4. Add container vulnerability scanning
