"""Test API router configuration."""
import pytest
from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings


def test_api_router_registration():
    """Test API router registration."""
    app = FastAPI()
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Verify router was registered
    assert any(
        route.path == f"{settings.API_V1_STR}/auth/login/access-token" for route in app.routes
    )
