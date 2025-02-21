"""Rate limiting configuration and validation."""
from typing import Dict, Optional
from pydantic import BaseModel, Field, validator

class RateLimitConfig(BaseModel):
    """
    Rate limiting configuration with validation.
    
    This class manages:
    1. Default rate limits
    2. Endpoint-specific limits
    3. Redis connection settings
    4. Validation rules
    """
    # Default settings
    default_window: int = Field(
        default=60,
        gt=0,
        description="Default time window in seconds"
    )
    default_max_requests: int = Field(
        default=100,
        gt=0,
        description="Default maximum requests per window"
    )
    
    # Endpoint-specific settings
    endpoint_limits: Dict[str, Dict[str, int]] = Field(
        default_factory=lambda: {
            "/api/v1/auth/token": {"window": 900, "max_requests": 5},
            "/api/v1/auth/register": {"window": 3600, "max_requests": 3},
        }
    )
    
    # Redis settings
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = None
    
    @validator("endpoint_limits")
    def validate_endpoint_limits(cls, v: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
        """Validate endpoint-specific rate limits."""
        for endpoint, limits in v.items():
            if not isinstance(limits, dict):
                raise ValueError(f"Invalid limits for endpoint {endpoint}")
            
            required_keys = {"window", "max_requests"}
            if not all(key in limits for key in required_keys):
                raise ValueError(
                    f"Endpoint {endpoint} missing required keys: {required_keys}"
                )
            
            if limits["window"] <= 0:
                raise ValueError(
                    f"Window for endpoint {endpoint} must be positive"
                )
            
            if limits["max_requests"] <= 0:
                raise ValueError(
                    f"Max requests for endpoint {endpoint} must be positive"
                )
        
        return v
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        
    def get_endpoint_limits(self, endpoint: str) -> Dict[str, int]:
        """Get rate limits for a specific endpoint or defaults."""
        return self.endpoint_limits.get(endpoint, {
            "window": self.default_window,
            "max_requests": self.default_max_requests
        })
