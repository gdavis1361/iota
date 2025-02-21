"""
Monitoring utilities for dynamic sampling and performance tracking.
"""
import time
from typing import Dict, Any, Optional
from threading import Lock
import structlog
from server.core.config import get_settings

logger = structlog.get_logger(__name__)

class PerformanceMonitor:
    """Monitor application performance and adjust sampling rates."""
    
    _instance = None
    _lock = Lock()
    
    def __init__(self):
        """Initialize performance monitor."""
        self.settings = get_settings()
        self.error_count = 0
        self.request_count = 0
        self.slow_request_count = 0
        self.last_reset = self._get_time()
        
        # Get thresholds from settings
        self.sampling_window = self.settings.SAMPLING_WINDOW_SECONDS
        self.slow_threshold_ms = self.settings.SLOW_REQUEST_THRESHOLD_MS
        self.error_rate_threshold = self.settings.ERROR_RATE_THRESHOLD
        self.slow_rate_threshold = self.settings.SLOW_RATE_THRESHOLD
        
        # Initialize sampling rates based on environment
        if self.settings.ENVIRONMENT == "test":
            self.current_traces_rate = 1.0
            self.current_profiles_rate = 1.0
        else:
            self.current_traces_rate = self.settings.SENTRY_TRACES_SAMPLE_RATE
            self.current_profiles_rate = self.settings.SENTRY_PROFILES_SAMPLE_RATE
    
    @classmethod
    def get_instance(cls) -> 'PerformanceMonitor':
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = PerformanceMonitor()
        return cls._instance
    
    def _get_time(self) -> float:
        """Get current time, allows for easier mocking in tests."""
        return float(time.time())
    
    def _should_reset_counters(self) -> bool:
        """Check if we should reset counters based on sampling window."""
        current_time = self._get_time()
        return (current_time - self.last_reset) > self.sampling_window
    
    def _reset_counters(self):
        """Reset performance counters."""
        self.error_count = 0
        self.request_count = 0
        self.slow_request_count = 0
        self.last_reset = self._get_time()
    
    def _calculate_new_sample_rates(self) -> Dict[str, float]:
        """Calculate new sampling rates based on metrics."""
        if self.request_count == 0:
            return {
                "traces": self.current_traces_rate,
                "profiles": self.current_profiles_rate
            }
        
        error_rate = self.error_count / self.request_count
        slow_rate = self.slow_request_count / self.request_count
        
        # Increase sampling if we're seeing issues
        if error_rate > self.error_rate_threshold or slow_rate > self.slow_rate_threshold:
            return {
                "traces": min(1.0, self.current_traces_rate * 2),
                "profiles": min(1.0, self.current_profiles_rate * 2)
            }
        
        # Decrease sampling if everything looks good
        if error_rate < (self.error_rate_threshold / 10) and slow_rate < (self.slow_rate_threshold / 10):
            return {
                "traces": max(0.01, self.current_traces_rate * 0.5),
                "profiles": max(0.01, self.current_profiles_rate * 0.5)
            }
        
        # Keep current rates
        return {
            "traces": self.current_traces_rate,
            "profiles": self.current_profiles_rate
        }
    
    def record_request(self, duration_ms: float, had_error: bool = False):
        """Record a request and its metrics."""
        with self._lock:
            # Check for reset before incrementing counters
            should_reset = self._should_reset_counters()
            
            # Calculate new rates before reset if needed
            if should_reset:
                new_rates = self._calculate_new_sample_rates()
                error_rate = self.error_count / max(1, self.request_count)
                slow_rate = self.slow_request_count / max(1, self.request_count)
                self._reset_counters()
                
                # Update rates if they changed
                if (new_rates["traces"] != self.current_traces_rate or 
                    new_rates["profiles"] != self.current_profiles_rate):
                    self.current_traces_rate = new_rates["traces"]
                    self.current_profiles_rate = new_rates["profiles"]
                    logger.info(
                        "Updated sampling rates",
                        traces_rate=self.current_traces_rate,
                        profiles_rate=self.current_profiles_rate,
                        error_rate=error_rate,
                        slow_rate=slow_rate
                    )
            
            # Now increment counters
            self.request_count += 1
            if had_error:
                self.error_count += 1
            if duration_ms > self.slow_threshold_ms:
                self.slow_request_count += 1
    
    def get_current_sample_rates(self) -> Dict[str, float]:
        """Get current sampling rates."""
        return {
            "traces": self.current_traces_rate,
            "profiles": self.current_profiles_rate
        }

# Initialize the monitor
monitor = PerformanceMonitor.get_instance()
