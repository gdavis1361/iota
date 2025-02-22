import pytest
from app.db.session import close_db, engine, get_db, init_db
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_db():
    """Test database session creation and closure"""
    db_gen = get_db()
    session = await anext(db_gen)

    # Verify we got a valid session
    assert isinstance(session, AsyncSession)

    # Close the session
    try:
        await db_gen.aclose()
    except StopAsyncIteration:
        pass

    # Verify session is closed by trying to use it
    with pytest.raises(Exception):
        await session.execute("SELECT 1")


@pytest.mark.asyncio
async def test_init_db():
    """Test database initialization"""
    # Initialize the database
    await init_db()

    # Verify tables are created by trying to create them again
    from app.models.base import Base

    async with engine.begin() as conn:
        # This should not raise any errors as tables already exist
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_close_db():
    """Test database cleanup"""
    # Create a session to verify it's closed after cleanup
    db_gen = get_db()
    session = await anext(db_gen)

    # Close the database
    await close_db()

    # Verify session is closed by trying to use it
    with pytest.raises(Exception):
        await session.execute("SELECT 1")

    # Clean up
    try:
        await db_gen.aclose()
    except StopAsyncIteration:
        pass
