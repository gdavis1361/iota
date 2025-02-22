"""Test database verification utilities."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_verify import check_database_tables, verify_database_connection
from app.db.session import get_db

pytestmark = pytest.mark.asyncio


async def test_database_connection():
    """Test database connection verification."""
    # Verify connection
    is_connected = await verify_database_connection()
    assert is_connected, "Database connection verification failed"


async def test_database_tables():
    """Test database table verification."""
    # Get database session
    async for db in get_db():
        # Check tables
        error = await check_database_tables(db)
        assert error is None, f"Database table verification failed: {error}"
        break  # We only need to test once


async def test_health_check_db_status(client):
    """Test that health check includes database status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert data["database"] in ["connected", "unavailable"]

    if data["database"] == "connected":
        assert data["status"] == "ok"
    else:
        assert data["status"] == "error"
