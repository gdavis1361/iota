from datetime import datetime

import pytest
from app.db.repositories.user import UserRepository
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation with all fields"""
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Test User",
    )

    user = await user_repo.create(user_data)
    assert user.email == user_data.email
    assert user.full_name == user_data.full_name
    assert user.hashed_password is not None
    assert user.hashed_password != user_data.password  # Verify password is hashed
    assert user.is_active is True
    assert user.is_verified is False
    assert user.is_superuser is False
    assert user.role == UserRole.USER
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession):
    """Test getting user by email - both existing and non-existing"""
    user_repo = UserRepository(db_session)

    # Create test user
    user_data = UserCreate(
        email="get_by_email@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Test User",
    )
    created_user = await user_repo.create(user_data)

    # Test getting existing user
    user = await user_repo.get_by_email(created_user.email)
    assert user is not None
    assert user.email == created_user.email

    # Test getting non-existing user
    user = await user_repo.get_by_email("nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_id(db_session: AsyncSession):
    """Test getting user by ID - both existing and non-existing"""
    user_repo = UserRepository(db_session)

    # Create test user
    user_data = UserCreate(
        email="get_by_id@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Test User",
    )
    created_user = await user_repo.create(user_data)

    # Test getting existing user
    user = await user_repo.get_by_id(created_user.id)
    assert user is not None
    assert user.id == created_user.id

    # Test getting non-existing user
    user = await user_repo.get_by_id(99999)
    assert user is None


@pytest.mark.asyncio
async def test_update_user_all_fields(db_session: AsyncSession):
    """Test updating all user fields"""
    user_repo = UserRepository(db_session)

    # Create test user
    user_data = UserCreate(
        email="update_test@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Original Name",
    )
    user = await user_repo.create(user_data)

    # Update all fields
    update_data = UserUpdate(
        password="newpassword123",
        confirm_password="newpassword123",
        full_name="Updated Name",
        is_active=False,
        is_verified=True,
        role=UserRole.ADMIN,
    )

    old_password = user.hashed_password
    updated_user = await user_repo.update(user, update_data)

    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_active is False
    assert updated_user.is_verified is True
    assert updated_user.role == UserRole.ADMIN
    assert updated_user.hashed_password != old_password
    assert isinstance(updated_user.updated_at, datetime)


@pytest.mark.asyncio
async def test_update_user_partial(db_session: AsyncSession):
    """Test partial user update"""
    user_repo = UserRepository(db_session)

    # Create test user
    user_data = UserCreate(
        email="partial_update@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Original Name",
    )
    user = await user_repo.create(user_data)

    # Update only name
    update_data = UserUpdate(full_name="Updated Name")
    updated_user = await user_repo.update(user, update_data)

    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_active == user.is_active
    assert updated_user.is_verified == user.is_verified
    assert updated_user.role == user.role
    assert updated_user.hashed_password == user.hashed_password


@pytest.mark.asyncio
async def test_delete_user(db_session: AsyncSession):
    """Test user deletion - both existing and non-existing"""
    user_repo = UserRepository(db_session)

    # Create test user
    user_data = UserCreate(
        email="delete_test@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Test User",
    )
    user = await user_repo.create(user_data)

    # Delete existing user
    deleted_user = await user_repo.delete(user.id)
    assert deleted_user is not None
    assert deleted_user.id == user.id

    # Verify user is deleted
    user = await user_repo.get_by_id(user.id)
    assert user is None

    # Try to delete non-existing user
    deleted_user = await user_repo.delete(99999)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_list_users(db_session: AsyncSession):
    """Test listing users with pagination"""
    user_repo = UserRepository(db_session)

    # Create multiple test users
    emails = [f"list_test_{i}@example.com" for i in range(5)]
    for email in emails:
        user_data = UserCreate(
            email=email,
            password="testpassword123",
            confirm_password="testpassword123",
            full_name=f"Test User {email}",
        )
        await user_repo.create(user_data)

    # Test default pagination
    users = await user_repo.list()
    assert len(users) >= 5

    # Test with skip and limit
    users = await user_repo.list(skip=2, limit=2)
    assert len(users) == 2

    # Test with large limit
    users = await user_repo.list(limit=1000)
    assert len(users) >= 5
