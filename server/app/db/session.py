from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.logging_config import diagnostics
from contextlib import asynccontextmanager
import logging
import time
from typing import Optional, AsyncGenerator

logger = logging.getLogger(__name__)

# Global engine and session maker
engine = None
async_session_maker = None

def record_metrics(name: str, value: float, tags: Optional[dict] = None):
    """Record metrics with error handling"""
    try:
        if hasattr(diagnostics, 'metrics') and hasattr(diagnostics.metrics, 'record'):
            diagnostics.metrics.record(name, value, tags or {})
    except Exception as e:
        logger.debug(f"Failed to record metrics for {name}: {str(e)}")

def init_engine():
    """Initialize database engine"""
    global engine, async_session_maker
    
    try:
        logger.info(f"Attempting to connect to database at: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
        logger.debug(f"Database connection parameters: user={settings.POSTGRES_USER}, db={settings.POSTGRES_DB}")
        
        # Create async engine
        engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URI,
            poolclass=NullPool,
            echo=settings.SQL_ECHO,
        )
        
        logger.info("Database engine created successfully")
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Session maker initialized")
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database connection: {str(e)}")
        raise

# Initialize engine on module load
init_engine()

# For backwards compatibility with existing tests
SessionLocal = async_session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with metrics tracking"""
    if engine is None or async_session_maker is None:
        init_engine()
        
    session = async_session_maker()
    start_time = time.time()
    
    try:
        # Track connection pool metrics safely
        if engine and hasattr(engine, 'pool'):
            pool = engine.pool
            if not isinstance(pool, NullPool):
                record_metrics("connection_pool_size", pool.size(), {"pool_name": "main"})
                if pool.size() > 0:  # Avoid division by zero
                    utilization = (pool.checkedin() + pool.checkedout()) / pool.size()
                    record_metrics("connection_pool_utilization", utilization, {"pool_name": "main"})
        
        yield session
        await session.commit()
        
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        # Record query timing
        query_time = time.time() - start_time
        record_metrics("db_query_time", query_time, {"operation": "session"})
        await session.close()

async def init_db():
    """Initialize database with metrics tracking"""
    try:
        if engine is None:
            init_engine()
            
        # Create initial connection to verify database access
        async with engine.begin() as conn:
            # Record successful initialization safely
            try:
                if hasattr(diagnostics, 'metrics') and hasattr(diagnostics.metrics, 'increment'):
                    diagnostics.metrics.increment("db_init_success")
            except Exception as e:
                logger.debug(f"Failed to record init success metric: {str(e)}")
                
            logger.info("Database initialized successfully")
            
    except SQLAlchemyError as e:
        # Record initialization failure safely
        try:
            if hasattr(diagnostics, 'metrics') and hasattr(diagnostics.metrics, 'increment'):
                diagnostics.metrics.increment("db_init_failure")
        except Exception as metric_e:
            logger.debug(f"Failed to record init failure metric: {str(metric_e)}")
            
        logger.error(f"Database initialization failed: {str(e)}")
        raise

async def close_db():
    """Close database connections"""
    global engine, async_session_maker
    
    if engine:
        await engine.dispose()
        engine = None
        async_session_maker = None
        logger.info("Database connections closed")
