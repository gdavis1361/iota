"""
Shared pytest fixtures and configuration.
"""

import logging
import os
from asyncio import AbstractEventLoop, new_event_loop
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator

import pytest
import pytest_asyncio
import structlog
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Configure logging
logger = structlog.get_logger()

# Set test environment variables
os.environ.update(
    {
        "ENVIRONMENT": "testing",
        "SERVER_HOST": "http://test",
        "SERVER_NAME": "IOTA Test Server",
        "PROJECT_NAME": "IOTA",
        "API_V1_STR": "/api/v1",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_DB": "jsquared_test",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "SECRET_KEY": "test_secret_key_for_testing_only",
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost/jsquared_test",
    }
)

from app.core.config import Settings, get_settings
# Import all models to ensure they are registered with metadata
from app.db.base import Base  # This imports all models
from app.db.session import get_db
from app.main import app as fastapi_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine."""
    logger.info("creating_test_database_engine")

    test_engine = create_async_engine(
        os.environ["DATABASE_URL"],
        echo=True,
        future=True,
        pool_pre_ping=True,  # Enable connection health checks
    )

    # Create all tables
    async with test_engine.begin() as conn:
        logger.info("dropping_existing_tables")
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("creating_test_tables")
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Clean up
    async with test_engine.begin() as conn:
        logger.info("cleaning_up_test_database")
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()
    logger.info("test_database_engine_disposed")


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    """Create a nested transaction and rollback after the test."""
    # Create a connection
    async with engine.connect() as connection:
        # Begin a transaction
        await connection.begin()

        # Begin a nested transaction (SAVEPOINT)
        await connection.begin_nested()

        # Create session with the nested transaction
        session = AsyncSession(bind=connection, expire_on_commit=False)

        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database session injection."""
    try:
        # Override the get_db dependency
        async def get_test_db():
            yield db_session

        fastapi_app.dependency_overrides[get_db] = get_test_db

        # Use test server host without API prefix since FastAPI adds it
        base_url = os.environ["SERVER_HOST"]

        async with AsyncClient(
            app=fastapi_app,
            base_url=base_url,
            follow_redirects=True,
        ) as test_client:
            yield test_client

    finally:
        # Always clean up dependency override
        fastapi_app.dependency_overrides.clear()


@pytest.fixture
def settings() -> Settings:
    """Get test settings."""
    return get_settings()


# Add SQL query logging for debugging
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query before execution."""
    logger.debug("sql_query_starting", statement=statement, parameters=parameters)


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query after execution."""
    logger.debug("sql_query_completed", statement=statement, parameters=parameters)
