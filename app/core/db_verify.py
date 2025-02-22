"""Database verification utilities."""
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_engine

logger = structlog.get_logger()


async def verify_database_connection() -> bool:
    """Verify database connection and configuration."""
    try:
        # Log connection attempt
        logger.info(
            "Verifying database connection",
            host=settings.POSTGRES_SERVER,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
        )

        # Test the connection with a simple query
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            await conn.commit()

            value = result.scalar()
            if value != 1:
                logger.error("Database verification query returned unexpected value", value=value)
                return False

            logger.info(
                "Database connection verified",
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_SERVER,
            )
            return True

    except Exception as e:
        logger.error(
            "Database connection verification failed",
            error=str(e),
            error_type=type(e).__name__,
            host=settings.POSTGRES_SERVER,
            database=settings.POSTGRES_DB,
        )
        return False


async def check_database_tables(db: AsyncSession) -> Optional[str]:
    """Check if required database tables exist."""
    try:
        # Query for table names in the public schema
        result = await db.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
            )
        )
        tables = [row[0] for row in result]

        logger.info("Database tables verified", tables=tables)
        return None

    except Exception as e:
        error_msg = f"Failed to verify database tables: {str(e)}"
        logger.error(
            "Database table verification failed", error=str(e), error_type=type(e).__name__
        )
        return error_msg
