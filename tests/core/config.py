"""Test configuration settings."""
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import EnvironmentType, Settings
from app.db.base import Base

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Test settings with database overrides
test_settings = Settings(
    ENVIRONMENT=EnvironmentType.TESTING,
    POSTGRES_DB="jsquared_test",  # Use a separate test database
    SQL_ECHO=True,
    DEBUG=True,
    SECRET_KEY="test_secret_key_for_testing_only",  # Required field
    ACCESS_TOKEN_EXPIRE_MINUTES=60,  # Longer expiration for testing
)

# Create engine with proper URL and configuration
engine = create_async_engine(
    str(test_settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    echo=test_settings.SQL_ECHO,
    pool_size=5,
    max_overflow=10,
    echo_pool=True,  # Log pool events
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database session for testing."""
    async with async_session_maker() as session:
        async with session.begin():
            try:
                yield session
            finally:
                await session.rollback()  # Ensure transaction is rolled back


async def setup_test_db() -> None:
    """Set up test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Test database tables created")


async def teardown_test_db() -> None:
    """Tear down test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Test database tables dropped")
