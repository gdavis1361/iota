"""Test API dependencies."""
import pytest
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings_dependency
from app.core.config import Settings


@pytest.mark.asyncio
async def test_get_db():
    """Test database session dependency."""
    # Get database generator
    db_gen = get_db()

    # Get session from generator
    session = None
    async for s in db_gen:
        session = s
        break

    assert isinstance(session, AsyncSession)

    try:
        # Test session is usable
        result = await session.execute(text("SELECT 1"))
        row = result.scalar()
        assert row == 1
        await session.commit()
    finally:
        # Clean up
        await session.close()


def test_get_settings():
    """Test settings dependency."""
    # Get settings
    settings = get_settings_dependency()
    assert isinstance(settings, Settings)

    # Verify essential settings
    assert settings.PROJECT_NAME == "IOTA"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
