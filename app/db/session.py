"""Database session management."""
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create engine with proper URL and configuration
async_engine = create_async_engine(
    str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    echo=settings.SQL_ECHO,
    pool_size=5,
    max_overflow=10,
    echo_pool=True,  # Log pool events
)

# Create session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with transaction."""
    async with async_session_maker() as session:
        async with session.begin():
            try:
                yield session
            except:
                await session.rollback()
                raise
            finally:
                await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with get_transaction() as session:
        yield session
