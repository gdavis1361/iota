"""Test configuration and fixtures."""
import logging

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from tests.core.config import async_session_maker, engine, test_settings

# Configure logging
logger = logging.getLogger("test_transactions")
logger.setLevel(logging.DEBUG)


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create database tables before tests and drop them after."""
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            logger.debug("Successfully created all tables")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise e
    yield
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
            logger.debug("Successfully dropped all tables")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise e


@pytest_asyncio.fixture
async def async_session(setup_database) -> AsyncSession:
    """Create a fresh SQLAlchemy AsyncSession for each test."""
    async with async_session_maker() as session:
        async with session.begin():
            yield session


@pytest.fixture
def client(async_session: AsyncSession) -> TestClient:
    """Create a test client using the test database."""

    async def override_get_db():
        try:
            yield async_session
        finally:
            pass  # Session cleanup is handled by the async_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
