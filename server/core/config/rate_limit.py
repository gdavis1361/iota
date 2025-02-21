"""Rate limiting configuration with validation."""
from typing import Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

class EndpointLimit(BaseModel):
    """Configuration for endpoint-specific rate limits."""
    window: int = Field(..., gt=0, description="Time window in seconds")
    max_requests: int = Field(..., gt=0, description="Maximum requests allowed in window")

class RateLimitConfig(BaseModel):
    """Rate limiting configuration with validation."""
    model_config = ConfigDict(
        frozen=True,  # Make config immutable
        validate_assignment=True
    )
    
    # Default limits
    default_window: int = Field(
        60, gt=0,
        description="Default time window in seconds"
    )
    default_max_requests: int = Field(
        100, gt=0,
        description="Default maximum requests per window"
    )
    
    # Endpoint-specific limits
    endpoint_limits: Dict[str, EndpointLimit] = Field(
        default_factory=lambda: {
            # Login endpoint: 5 attempts per 15 minutes
            "/api/v1/auth/token": EndpointLimit(
                window=900,
                max_requests=5
            ),
            # Registration: 3 attempts per hour
            "/api/v1/auth/register": EndpointLimit(
                window=3600,
                max_requests=3
            )
        }
    )
    
    # Redis configuration
    redis_host: str = Field("localhost", description="Redis host")
    redis_port: int = Field(6379, gt=0, description="Redis port")
    redis_password: Optional[str] = Field(None, description="Redis password")

    def get_endpoint_limits(self, endpoint: str) -> Dict[str, int]:
        """Get rate limits for a specific endpoint or defaults."""
        return self.endpoint_limits.get(endpoint, {
            "window": self.default_window,
            "max_requests": self.default_max_requests
        })
