import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate

@pytest.fixture
async def db_session():
    # Assuming you have a function to create an async db session
    # Replace this with your actual implementation
    async with AsyncSession() as session:
        yield session

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation"""
    user_repo = UserRepository(db_session)
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "role": "USER"
    }
    user_in = UserCreate(**user_data)
    user = await user_repo.create(user_in)
    assert user.email == user_data["email"]
    assert user.full_name == user_data["full_name"]
    assert hasattr(user, "hashed_password")
    assert user.hashed_password != user_data["password"]
    assert user.is_active is True
    assert user.is_verified is False
    assert user.role == "USER"

@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession):
    """Test getting user by email"""
    user_repo = UserRepository(db_session)
    user_data = {
        "email": "test2@example.com",
        "password": "testpassword123",
        "full_name": "Test User 2",
        "role": "USER"
    }
    user_in = UserCreate(**user_data)
    created_user = await user_repo.create(user_in)
    
    found_user = await user_repo.get_by_email(user_data["email"])
    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.email == user_data["email"]

@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession):
    """Test user update"""
    user_repo = UserRepository(db_session)
    user_data = {
        "email": "test3@example.com",
        "password": "testpassword123",
        "full_name": "Test User 3",
        "role": "USER"
    }
    user_in = UserCreate(**user_data)
    user = await user_repo.create(user_in)
    
    update_data = UserUpdate(full_name="Updated Name")
    updated_user = await user_repo.update(user, update_data)
    assert updated_user.full_name == "Updated Name"
    assert updated_user.email == user_data["email"]
