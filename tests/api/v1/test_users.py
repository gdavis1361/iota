"""Test user endpoints."""
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate


@pytest.mark.asyncio
async def test_create_user(async_client: AsyncClient, db_session):
    """Test user creation."""
    # Test data
    user_data = {"email": "test@example.com", "password": "testpass123", "full_name": "Test User"}

    # Create user
    response = await async_client.post(f"{settings.API_V1_STR}/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify response
    user_response = response.json()
    assert user_response["email"] == user_data["email"]
    assert user_response["full_name"] == user_data["full_name"]
    assert user_response["is_active"] is True
    assert "id" in user_response
    assert "hashed_password" not in user_response

    # Verify database
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    db_user = result.scalar_one()
    assert db_user is not None
    assert db_user.email == user_data["email"]
    assert db_user.full_name == user_data["full_name"]
    assert db_user.is_active is True


@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client: AsyncClient, db_session):
    """Test creating user with duplicate email."""
    # Test data
    user_data = {"email": "test@example.com", "password": "testpass123", "full_name": "Test User"}

    # Create first user
    db_user = User(
        email=user_data["email"],
        hashed_password="dummyhash",
        full_name=user_data["full_name"],
        is_active=True,
    )
    db_session.add(db_user)
    await db_session.commit()

    # Try creating duplicate user
    response = await async_client.post(f"{settings.API_V1_STR}/users", json=user_data)
    assert response.status_code == status.HTTP_409_CONFLICT

    # Verify error message
    error_detail = response.json()["detail"]
    assert "Email already registered" in error_detail
