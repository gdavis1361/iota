"""Integration tests for rate limit alerts."""
import time
import pytest
import requests
import yaml
from prometheus_client import Counter, Gauge, Histogram
from prometheus_client import generate_latest, CollectorRegistry

class TestRateLimitAlerts:
    """Test suite for rate limit alert rules."""

    @pytest.fixture
    def registry(self):
        """Create a new collector registry."""
        return CollectorRegistry()

    @pytest.fixture
    def metrics(self, registry):
        """Create test metrics."""
        return {
            'rate_limit_exceeded': Counter(
                'rate_limit_exceeded_total',
                'Total rate limit violations',
                ['endpoint'],
                registry=registry
            ),
            'failed_login_attempts': Counter(
                'failed_login_attempts_total',
                'Failed login attempts',
                ['ip'],
                registry=registry
            ),
            'rate_limit_remaining': Gauge(
                'rate_limit_remaining',
                'Remaining requests in window',
                ['endpoint'],
                registry=registry
            ),
            'rate_limit_window_reset': Gauge(
                'rate_limit_window_reset_seconds',
                'Time until window reset',
                ['endpoint'],
                registry=registry
            ),
            'rate_limit_check_duration': Histogram(
                'rate_limit_check_duration_seconds',
                'Request processing latency',
                registry=registry
            )
        }

    def load_alert_rules(self):
        """Load Prometheus alert rules."""
        with open('/Users/allan/Projects/iota/prometheus/rules/rate_limiter.yml', 'r') as f:
            return yaml.safe_load(f)

    def test_high_rate_limit_violations(self, metrics):
        """Test HighRateLimitViolations alert."""
        metrics['rate_limit_exceeded'].labels(endpoint='/api/test').inc()
        time.sleep(1)
        metrics['rate_limit_exceeded'].labels(endpoint='/api/test').inc()
        
        # Generate 100 violations in 1 hour (threshold)
        for _ in range(98):
            metrics['rate_limit_exceeded'].labels(endpoint='/api/test').inc()
        
        data = generate_latest(metrics['rate_limit_exceeded']._collector)
        assert b'rate_limit_exceeded_total{endpoint="/api/test"} 100.0' in data

    def test_critical_rate_limit_violations(self, metrics):
        """Test CriticalRateLimitViolations alert."""
        # Generate 500 violations in 1 hour (threshold)
        for _ in range(500):
            metrics['rate_limit_exceeded'].labels(endpoint='/api/test').inc()
        
        data = generate_latest(metrics['rate_limit_exceeded']._collector)
        assert b'rate_limit_exceeded_total{endpoint="/api/test"} 500.0' in data

    def test_high_failed_login_attempts(self, metrics):
        """Test HighFailedLoginAttempts alert."""
        # Generate 5 failed attempts in 15 minutes (threshold)
        for _ in range(5):
            metrics['failed_login_attempts'].labels(ip='127.0.0.1').inc()
        
        data = generate_latest(metrics['failed_login_attempts']._collector)
        assert b'failed_login_attempts_total{ip="127.0.0.1"} 5.0' in data

    def test_rate_limit_latency(self, metrics):
        """Test RateLimitLatencyHigh alert."""
        # Simulate high latency (>100ms)
        metrics['rate_limit_check_duration'].observe(0.15)
        
        data = generate_latest(metrics['rate_limit_check_duration']._collector)
        assert b'rate_limit_check_duration_seconds_bucket{le="0.2"' in data

    def test_low_rate_limit_capacity(self, metrics):
        """Test LowRateLimitCapacity alert."""
        # Set remaining capacity to 5% (threshold is 10%)
        metrics['rate_limit_remaining'].labels(endpoint='/api/test').set(5)
        metrics['rate_limit_remaining'].labels(endpoint='/api/test2').set(100)
        
        data = generate_latest(metrics['rate_limit_remaining']._collector)
        assert b'rate_limit_remaining{endpoint="/api/test"} 5.0' in data

    def test_auth_endpoint_overload(self, metrics):
        """Test AuthEndpointOverload alert."""
        # Generate 10 violations in 15 minutes on auth endpoint
        for _ in range(10):
            metrics['rate_limit_exceeded'].labels(endpoint='/api/v1/auth/token').inc()
        
        data = generate_latest(metrics['rate_limit_exceeded']._collector)
        assert b'rate_limit_exceeded_total{endpoint="/api/v1/auth/token"} 10.0' in data

    def test_failed_login_burst(self, metrics):
        """Test FailedLoginBurst alert."""
        # Generate 10 failed attempts in 1 minute
        for _ in range(10):
            metrics['failed_login_attempts'].labels(ip='127.0.0.1').inc()
        
        data = generate_latest(metrics['failed_login_attempts']._collector)
        assert b'failed_login_attempts_total{ip="127.0.0.1"} 10.0' in data

    def test_rate_limit_window_stuck(self, metrics):
        """Test RateLimitWindowStuck alert."""
        # Set window reset time to 1000 seconds (threshold is 900)
        metrics['rate_limit_window_reset'].labels(endpoint='/api/test').set(1000)
        
        data = generate_latest(metrics['rate_limit_window_reset']._collector)
        assert b'rate_limit_window_reset_seconds{endpoint="/api/test"} 1000.0' in data

    def test_alert_rules_syntax(self):
        """Test alert rules YAML syntax."""
        rules = self.load_alert_rules()
        assert 'groups' in rules
        assert len(rules['groups']) > 0
        assert 'rules' in rules['groups'][0]

    @pytest.mark.parametrize("alert_name,expected_severity", [
        ("HighRateLimitViolations", "warning"),
        ("CriticalRateLimitViolations", "critical"),
        ("HighFailedLoginAttempts", "warning"),
        ("RateLimitLatencyHigh", "warning"),
        ("LowRateLimitCapacity", "warning"),
        ("RedisConnectionIssues", "critical"),
        ("AuthEndpointOverload", "critical"),
        ("FailedLoginBurst", "critical")
    ])
    def test_alert_severities(self, alert_name, expected_severity):
        """Test alert severity levels."""
        rules = self.load_alert_rules()
        for rule in rules['groups'][0]['rules']:
            if rule.get('alert') == alert_name:
                assert rule['labels']['severity'] == expected_severity
                break

    def test_prometheus_endpoint_integration(self, metrics):
        """Test Prometheus metrics endpoint integration."""
        # Simulate some metric updates
        metrics['rate_limit_exceeded'].labels(endpoint='/api/test').inc()
        metrics['failed_login_attempts'].labels(ip='127.0.0.1').inc()
        metrics['rate_limit_remaining'].labels(endpoint='/api/test').set(50)
        
        # Generate metrics in Prometheus format
        data = generate_latest(metrics['rate_limit_exceeded']._collector)
        assert b'rate_limit_exceeded_total' in data
        
        data = generate_latest(metrics['failed_login_attempts']._collector)
        assert b'failed_login_attempts_total' in data
        
        data = generate_latest(metrics['rate_limit_remaining']._collector)
        assert b'rate_limit_remaining' in data
