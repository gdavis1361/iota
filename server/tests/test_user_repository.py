import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.models.enums import UserRole  # Import UserRole enum

@pytest_asyncio.fixture
async def user_repo(db: AsyncSession) -> UserRepository:
    """User repository fixture"""
    return UserRepository(db)

@pytest_asyncio.fixture
async def test_user_data() -> dict:
    """Test user data"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
        "full_name": "Test User"
    }

@pytest.mark.asyncio
async def test_create_user(user_repo: UserRepository, test_user_data: dict):
    """Test user creation"""
    user_in = UserCreate(**test_user_data)
    user = await user_repo.create(user_in)
    
    assert user.email == test_user_data["email"]
    assert user.full_name == test_user_data["full_name"]
    assert verify_password(test_user_data["password"], user.hashed_password)
    assert user.is_active is True
    assert user.is_verified is False
    assert user.role == UserRole.USER

@pytest.mark.asyncio
async def test_get_by_email(user_repo: UserRepository, test_user_data: dict):
    """Test getting user by email"""
    # Create user first
    user_in = UserCreate(**test_user_data)
    created_user = await user_repo.create(user_in)
    
    # Test get by email
    user = await user_repo.get_by_email(test_user_data["email"])
    assert user is not None
    assert user.id == created_user.id
    assert user.email == test_user_data["email"]
    
    # Test non-existent email
    user = await user_repo.get_by_email("nonexistent@example.com")
    assert user is None

@pytest.mark.asyncio
async def test_get_by_id(user_repo: UserRepository, test_user_data: dict):
    """Test getting user by ID"""
    # Create user first
    user_in = UserCreate(**test_user_data)
    created_user = await user_repo.create(user_in)
    
    # Test get by ID
    user = await user_repo.get_by_id(created_user.id)
    assert user is not None
    assert user.id == created_user.id
    assert user.email == test_user_data["email"]
    
    # Test non-existent ID
    user = await user_repo.get_by_id(999999)
    assert user is None

@pytest.mark.asyncio
async def test_update_user(user_repo: UserRepository, test_user_data: dict):
    """Test user update"""
    # Create user first
    user_in = UserCreate(**test_user_data)
    user = await user_repo.create(user_in)
    
    # Update user
    update_data = UserUpdate(
        full_name="Updated Name",
        is_active=False,
        is_verified=True,
        role="ADMIN",
        password="newpassword123"
    )
    updated_user = await user_repo.update(user, update_data)
    
    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_active is False
    assert updated_user.is_verified is True
    assert updated_user.role == "ADMIN"
    assert updated_user.email == test_user_data["email"]  # Email shouldn't change
    assert verify_password("newpassword123", updated_user.hashed_password)  # Verify password was updated

@pytest.mark.asyncio
async def test_delete_user(user_repo: UserRepository, test_user_data: dict):
    """Test user deletion"""
    # Create user first
    user_in = UserCreate(**test_user_data)
    user = await user_repo.create(user_in)
    
    # Delete user
    deleted_user = await user_repo.delete(user.id)
    assert deleted_user.id == user.id
    
    # Verify user is deleted
    user = await user_repo.get_by_id(deleted_user.id)
    assert user is None

    # Try to delete non-existent user
    non_existent = await user_repo.delete(999999)
    assert non_existent is None

@pytest.mark.asyncio
async def test_list_users(user_repo: UserRepository):
    """Test listing users"""
    # Create multiple users
    users_data = [
        UserCreate(email="user1@example.com", password="password123", full_name="User 1", confirm_password="password123"),
        UserCreate(email="user2@example.com", password="password123", full_name="User 2", confirm_password="password123"),
        UserCreate(email="user3@example.com", password="password123", full_name="User 3", confirm_password="password123"),
        UserCreate(email="user4@example.com", password="password123", full_name="User 4", confirm_password="password123"),
        UserCreate(email="user5@example.com", password="password123", full_name="User 5", confirm_password="password123")
    ]
    
    created_users = []
    for user_data in users_data:
        user = await user_repo.create(user_data)
        created_users.append(user)

    # Test default list (no skip, default limit)
    users = await user_repo.list()
    assert len(users) >= 5  # Could be more if other tests created users
    assert all(isinstance(user, User) for user in users)

    # Test with skip
    users_skip = await user_repo.list(skip=2)
    assert len(users_skip) >= 3  # At least 3 users (5 - 2 skipped)
    assert users_skip[0].id != users[0].id  # First user should be different after skip

    # Test with limit
    users_limit = await user_repo.list(limit=2)
    assert len(users_limit) == 2
    assert users_limit[0].id == users[0].id  # First user should be same as no skip
