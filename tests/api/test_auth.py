"""Test cases for authentication endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from tests.utils.utils import random_email, random_lower_string


@pytest.mark.asyncio
async def test_login_access_token(
    db_session: AsyncSession, test_settings: Settings, async_client: AsyncClient
) -> None:
    """Test login endpoint."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    data = {
        "username": email,
        "password": password,
    }
    response = await async_client.post(f"{test_settings.API_V1_STR}/auth/login", data=data)
    assert response.status_code == 200
    content = response.json()
    assert content["access_token"]
    assert content["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_access_token_incorrect_password(
    db_session: AsyncSession, test_settings: Settings, async_client: AsyncClient
) -> None:
    """Test login with incorrect password."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    data = {
        "username": email,
        "password": "wrong-password",
    }
    response = await async_client.post(f"{test_settings.API_V1_STR}/auth/login", data=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_access_token_inactive_user(
    db_session: AsyncSession, test_settings: Settings, async_client: AsyncClient
) -> None:
    """Test login with inactive user."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    data = {
        "username": email,
        "password": password,
    }
    response = await async_client.post(f"{test_settings.API_V1_STR}/auth/login", data=data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_signup(
    db_session: AsyncSession, test_settings: Settings, async_client: AsyncClient
) -> None:
    """Test user registration."""
    data = {
        "email": random_email(),
        "password": "Password123",
        "confirm_password": "Password123",
        "full_name": random_lower_string(),
    }
    response = await async_client.post(f"{test_settings.API_V1_STR}/auth/signup", json=data)
    assert response.status_code == 200
    content = response.json()
    assert content["access_token"]
    assert content["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_signup_existing_user(
    db_session: AsyncSession, test_settings: Settings, async_client: AsyncClient
) -> None:
    """Test registration with existing email."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    data = {
        "email": email,
        "password": "Password123",
        "confirm_password": "Password123",
        "full_name": random_lower_string(),
    }
    response = await async_client.post(f"{test_settings.API_V1_STR}/auth/signup", json=data)
    assert response.status_code == 400
    assert response.json()["detail"] == "The user with this username already exists in the system"


@pytest.mark.asyncio
async def test_test_token(
    db_session: AsyncSession, test_settings: Settings, async_client: AsyncClient
) -> None:
    """Test token validation endpoint."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    access_token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.post(
        f"{test_settings.API_V1_STR}/auth/test-token",
        headers=headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == email
