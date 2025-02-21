import asyncio
import pytest
import pytest_asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.engine.url import make_url
from fastapi import FastAPI
from sqlalchemy import text
import subprocess
import os
from dotenv import load_dotenv
import redis.asyncio as redis

from app.core.config import settings
from app.db.base import Base
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import create_access_token, get_password_hash

# Load test environment variables
load_dotenv(".env.test")

# Create async engine for tests
TEST_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI
engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

# Create async session factory
TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    """Yield the SQLAlchemy engine"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get a TestingSessionLocal instance that rolls back all changes"""
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    async_session = TestingSessionLocal(bind=connection)
    
    yield async_session
    
    await async_session.close()
    await transaction.rollback()
    await connection.close()

@pytest_asyncio.fixture(scope="session")
async def redis_pool():
    """Create Redis connection pool for testing."""
    pool = redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=2,
        decode_responses=True
    )
    yield pool
    await pool.disconnect()

@pytest_asyncio.fixture
async def redis_client(redis_pool, app: FastAPI):
    """Create Redis client and patch it into the app for testing."""
    from app.core.redis import get_redis_client, close_redis_client
    
    client = redis.Redis(connection_pool=redis_pool)
    
    # Clear any existing data
    await client.flushall()
    
    async def override_get_redis():
        return client
    
    app.dependency_overrides[get_redis_client] = override_get_redis
    
    yield client
    
    # Clean up
    await client.close()
    app.dependency_overrides.pop(get_redis_client, None)

@pytest_asyncio.fixture
async def test_app(db_session: AsyncSession, redis_client) -> FastAPI:
    """Create FastAPI test application with all dependencies."""
    from app.main import app
    from app.api.deps import get_db
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    return app

@pytest_asyncio.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with proper host configuration."""
    async with AsyncClient(
        app=test_app,
        base_url="http://testserver",
        headers={"host": "testserver"}
    ) as client:
        yield client

@pytest_asyncio.fixture
async def client(test_client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    yield test_client

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user_repo = UserRepository(db_session)
    user_in = UserCreate(
        email="test@example.com",
        password="testpass123",
        full_name="Test User"
    )
    
    # Check if test user exists
    existing_user = await user_repo.get_by_email(email=user_in.email)
    if existing_user:
        return existing_user
        
    user = await user_repo.create(obj_in=user_in)
    await db_session.commit()
    return user

@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers."""
    access_token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {access_token}"}
