import pytest
import pytest_asyncio
from app.core.security import create_access_token, get_password_hash
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def test_user_data() -> dict:
    """Test user data"""
    return {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
    }


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, test_user_data):
    """Test user registration"""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, test_user_data, db: AsyncSession):
    """Test user login"""
    # First create a user
    user_repo = UserRepository(db)
    user_in = UserCreate(**test_user_data)
    await user_repo.create(user_in)

    # Then try to login
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user_data, db: AsyncSession):
    """Test getting current user info"""
    # First create a user
    user_repo = UserRepository(db)
    user_in = UserCreate(**test_user_data)
    user = await user_repo.create(user_in)

    # Create token and test
    token = create_access_token({"sub": user.email})
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert "hashed_password" not in data
