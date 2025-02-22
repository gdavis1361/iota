"""Database session configuration."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_engine() -> AsyncEngine:
    """Create database engine."""
    logger.info(
        "Attempting to connect to database at: %s:%s",
        settings.POSTGRES_SERVER,
        settings.POSTGRES_PORT,
    )
    logger.debug(
        "Database connection parameters: user=%s, db=%s",
        settings.POSTGRES_USER,
        settings.POSTGRES_DB,
    )

    # Log the database URL for debugging
    logger.debug("Database URL: %s", settings.DATABASE_URL)

    # Convert postgresql:// to postgresql+asyncpg:// for SQLAlchemy
    db_url = str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")
    logger.debug("Using database URL: %s", db_url)

    return create_async_engine(
        db_url,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Initialize engine and session factory
engine = create_engine()
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# For backwards compatibility with existing tests
SessionLocal = async_session_factory
AsyncSessionLocal = async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with explicit transaction management.

    This function provides a database session with proper transaction handling:
    - Each session is created fresh from the session factory
    - Transactions are explicitly started with session.begin()
    - Changes are committed on success, rolled back on failure
    - Sessions are properly closed after use
    """
    async with async_session_factory() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
