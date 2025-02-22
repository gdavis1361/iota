"""
Basic tests to verify test infrastructure is working correctly.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


@pytest.mark.asyncio
async def test_database_session(db_session: AsyncSession):
    """Verify database session is working."""
    # Execute a simple query
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1, "Database session not working correctly"


@pytest.mark.asyncio
async def test_async_client():
    """Verify async client is working."""
    # Create test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make request to API health endpoint
        response = await client.get("/api/v1/health")

        # Verify response without awaiting
        assert response.status_code == 200, (
            f"Health check endpoint not responding. "
            f"Status: {response.status_code}, "
            f"Body: {response.text}"
        )

        # Parse JSON response
        data = response.json()
        assert data["status"] == "ok", f"Health check returned unexpected status: {data}"


@pytest.mark.asyncio
async def test_environment_setup(settings):
    """Verify test environment is configured correctly."""
    assert settings.ENVIRONMENT == "testing"
    assert settings.SERVER_HOST == "http://test"
    assert settings.API_V1_STR == "/api/v1"
