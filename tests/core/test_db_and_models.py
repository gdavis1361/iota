"""Test database initialization and model functionality."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.init import Base
from app.models.enums import UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_db_session():
    """Test database session management."""
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        await session.close()
        break


@pytest.mark.asyncio
async def test_user_role_enum():
    """Test UserRole enum functionality."""
    # Test enum values
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.USER == "USER"
    assert UserRole.GUEST == "GUEST"

    # Test enum membership
    assert "ADMIN" in UserRole.__members__
    assert "USER" in UserRole.__members__
    assert "GUEST" in UserRole.__members__


@pytest.mark.asyncio
async def test_base_model_inheritance():
    """Test Base model functionality."""
    # Verify User model inherits from Base
    assert issubclass(User, Base)

    # Test table name convention
    assert User.__tablename__ == "users"


@pytest.mark.asyncio
async def test_db_initialization(async_session: AsyncSession):
    """Test database initialization with models."""
    # Create a test user
    test_user = User(email="test@example.com", hashed_password="hashed", is_active=True)

    # Add and commit
    async_session.add(test_user)
    await async_session.commit()
    await async_session.refresh(test_user)

    # Query back
    result = await async_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one()

    # Verify fields
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.id is not None
