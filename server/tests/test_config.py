import pytest
import asyncio
from app.core.config import settings, Settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from redis import Redis
import asyncpg

@pytest.mark.asyncio
async def test_database_url():
    """Test database URL configuration"""
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    
    # Create test database if it doesn't exist
    conn = await asyncpg.connect(
        database="postgres",
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=int(settings.POSTGRES_PORT)
    )
    
    # Disconnect all users from the database we will drop
    await conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1", settings.POSTGRES_DB)
    await conn.execute(f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB}")
    await conn.execute(f"CREATE DATABASE {settings.POSTGRES_DB}")
    await conn.close()
    
    # Now test the connection
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert (await result.scalar()) == 1
    await engine.dispose()

def test_redis_url():
    """Test Redis URL configuration"""
    assert settings.REDIS_URL.startswith("redis://")
    redis = Redis.from_url(settings.REDIS_URL)
    assert redis.ping()

def test_jwt_settings():
    """Test JWT configuration"""
    assert settings.SECRET_KEY is not None
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

def test_cors_settings():
    """Test CORS configuration"""
    assert settings.BACKEND_CORS_ORIGINS is not None
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)

@pytest.mark.asyncio
async def test_database_url_validator():
    """Test database URL validator"""
    test_settings = Settings(
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_pass",
        POSTGRES_DB="test_db",
        POSTGRES_SERVER="localhost",
        POSTGRES_PORT="5432"
    )
    assert test_settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    
    # Test with explicit URL
    test_settings = Settings(
        DATABASE_URL="postgresql://user:pass@host:5432/db"
    )
    assert test_settings.DATABASE_URL.startswith("postgresql+asyncpg://")

def test_redis_url_validator():
    """Test Redis URL validator"""
    test_settings = Settings(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0
    )
    assert test_settings.REDIS_URL.startswith("redis://")
    
    # Test with password
    test_settings = Settings(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0,
        REDIS_PASSWORD="secret"
    )
    assert "secret" in test_settings.REDIS_URL
    assert test_settings.REDIS_URL.startswith("redis://:")
