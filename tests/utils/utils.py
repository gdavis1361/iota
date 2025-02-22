"""Test utilities and helper functions."""
import random
import string
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def random_lower_string(length: int = 32) -> str:
    """Generate a random lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email address."""
    return f"{random_lower_string()}@example.com"


async def verify_table_exists(session: AsyncSession, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = await session.execute(text(f"SELECT to_regclass('public.{table_name}')"))
    return result.scalar() is not None


async def verify_tables_exist(session: AsyncSession, table_names: List[str]) -> None:
    """Verify that all specified tables exist in the database."""
    for table_name in table_names:
        exists = await verify_table_exists(session, table_name)
        assert exists, f"Table '{table_name}' does not exist"
