# Redis Sentinel Monitoring System

## Overview
This monitoring system provides comprehensive observability for the Redis Sentinel cluster using Prometheus and Grafana. It tracks key metrics including memory usage, sentinel health, failover events, and performance indicators.

## Components

### 1. Prometheus Exporters
- **Redis Exporter** (Port 9121): Collects metrics from Redis master
- **Sentinel Exporter** (Port 9122): Collects metrics from Redis Sentinel

### 2. Recording Rules
Located in `/prometheus/rules/redis_recording.yml`:
- `redis_mem_usage_percent`: Memory usage percentage
- `redis_commands_rate`: Command throughput per second
- `redis_network_in_rate`: Network input bytes/sec
- `redis_network_out_rate`: Network output bytes/sec
- `redis_healthy_sentinels`: Count of healthy sentinel nodes
- `redis_failover_hourly`: Failover events per hour

### 3. Alert Rules
Located in `/prometheus/rules/redis_alerts.yml`:

| Alert Name | Condition | Severity | Duration |
|------------|-----------|----------|-----------|
| RedisHighMemoryUsage | Memory > 80% | Warning | 5m |
| RedisFrequentFailovers | >3 failovers/hour | Critical | 0m |
| RedisLowSentinelCount | <2 healthy sentinels | Critical | 1m |
| RedisHighCommandRate | >10000 cmds/sec | Warning | 5m |

## Monitoring Stack

### Docker Services
```yaml
services:
  prometheus:
    port: 9090
    volumes:
      - ./prometheus:/etc/prometheus
      - ./prometheus/rules:/etc/prometheus/rules

  grafana:
    port: 3000
    default credentials: admin/admin
```

### Access Points
- Grafana Dashboard: http://localhost:3000
- Prometheus UI: http://localhost:9090
- Redis Exporter Metrics: http://localhost:9121/metrics
- Sentinel Exporter Metrics: http://localhost:9122/metrics

## Note on Implementation
**Important:** While the monitoring infrastructure (Prometheus + Grafana) has been set up with all necessary configurations, the dashboard visualization was not fully implemented due to the cumbersome nature of the Prometheus/Grafana UI setup process. In retrospect, there are likely more straightforward monitoring solutions available that don't require as much manual configuration.

Alternative approaches that could be explored:
1. Cloud-based monitoring solutions (e.g., DataDog, New Relic)
2. Simpler, single-binary solutions
3. Direct Redis monitoring tools with built-in visualization

The current setup provides the foundational metrics collection and alerting infrastructure, but the visualization layer can be replaced or enhanced based on team preferences.

## Maintenance

### Restarting Services
```bash
cd monitoring
docker compose -f docker-compose.monitoring.yml restart prometheus grafana
```

### Updating Alert Rules
1. Edit rules in `/prometheus/rules/`
2. Restart Prometheus to apply changes
3. Verify in Prometheus UI -> Status -> Rules

### Adding New Metrics
1. Add recording rule in `redis_recording.yml`
2. Add alert rule in `redis_alerts.yml` if needed
3. Restart Prometheus
4. Add panel to Grafana dashboard

## Troubleshooting

### Common Issues
1. **Missing Metrics**
   - Check exporter connectivity
   - Verify Redis/Sentinel ports
   - Check Prometheus targets

2. **Alert Not Firing**
   - Verify rule syntax
   - Check metric values
   - Confirm evaluation period

3. **Dashboard Issues**
   - Verify Prometheus data source
   - Check metric names
   - Confirm time range

## Future Enhancements
1. Add notification channels (Slack, email)
2. Implement machine learning-based anomaly detection
3. Add network performance metrics
4. Create more advanced visualization panels
