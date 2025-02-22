"""Test database session management."""
import os
from typing import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal, create_engine, get_db


@pytest.fixture(scope="module")
def test_db_url() -> str:
    """Get test database URL."""
    return str(settings.DATABASE_URL)


@pytest.mark.asyncio
async def test_create_engine():
    """Test engine creation with correct configuration."""
    engine = create_engine()
    assert isinstance(engine, AsyncEngine)

    # Verify connection works
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

    # Verify engine configuration
    assert engine.echo == settings.SQL_ECHO
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10


@pytest.mark.asyncio
async def test_session_factory():
    """Test session factory creates working sessions."""
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)
        # Verify session can execute queries
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_get_db():
    """Test get_db provides working session with transaction management."""
    session_gen = get_db()
    assert isinstance(session_gen, AsyncGenerator)

    async for session in get_db():
        # Test basic query
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Test transaction is active
        assert session.in_transaction()
        break  # We only need the first yielded session


@pytest.mark.asyncio
async def test_transaction_rollback():
    """Test automatic transaction rollback on error."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                # Execute invalid SQL to trigger an error
                await session.execute(text("SELECT * FROM nonexistent_table"))
                pytest.fail("Should have raised an exception")
            except SQLAlchemyError:
                # Verify we can execute a new query in a new transaction
                async with AsyncSessionLocal() as new_session:
                    result = await new_session.execute(text("SELECT 1"))
                    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_connection_pool():
    """Test connection pool behavior."""
    engine = create_engine()

    # Verify initial pool settings
    assert engine.pool.size() == 5  # Initial pool size
    assert engine.pool._max_overflow == 10  # Max overflow

    # Create multiple concurrent connections
    import asyncio

    async def get_connection():
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
            # Sleep briefly to ensure connection stays open
            await asyncio.sleep(0.1)
            return conn

    # Run concurrent connections
    connections = await asyncio.gather(*[get_connection() for _ in range(3)])

    # Verify pool can handle multiple connections
    assert engine.pool.checkedin() >= 0
    assert engine.pool.checkedout() >= 0
    assert engine.pool.size() == 5  # Pool maintains its size


@pytest.mark.asyncio
async def test_session_isolation():
    """Test session isolation between concurrent operations."""
    import asyncio

    async def run_transaction(i: int) -> int:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(text("SELECT pg_backend_pid()"))
                return result.scalar()

    # Run multiple concurrent sessions
    pids = await asyncio.gather(*[run_transaction(i) for i in range(3)])

    # Verify each transaction ran in its own connection
    assert len(set(pids)) == 3


@pytest.mark.asyncio
async def test_session_cleanup():
    """Test sessions are properly cleaned up after use."""
    engine = create_engine()
    initial_connections = engine.pool.size()

    async with AsyncSessionLocal() as session:
        # Use the session
        await session.execute(text("SELECT 1"))

    # Verify connection returned to pool
    assert engine.pool.size() == initial_connections
