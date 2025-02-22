"""Test authentication endpoint functionality."""
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils.factories import create_test_user


@pytest.mark.asyncio
async def test_login_success(async_session: AsyncSession, app: FastAPI, async_client: AsyncClient):
    """Test successful login with valid credentials."""
    # Create test user with factory
    user = create_test_user()
    async_session.add(user)
    await async_session.commit()

    # Attempt login
    response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": user.email, "password": "testpass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test login failure with invalid password."""
    # Create test user with factory
    user = create_test_user()
    async_session.add(user)
    await async_session.commit()

    # Attempt login with wrong password
    response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": user.email, "password": "wrongpass"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_inactive_user(
    async_session: AsyncSession, app: FastAPI, async_client: AsyncClient
):
    """Test login failure with inactive user."""
    # Create inactive test user with factory
    user = create_test_user(is_active=False)
    async_session.add(user)
    await async_session.commit()

    # Attempt login
    response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": user.email, "password": "testpass123"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_login_nonexistent_user(app: FastAPI, async_client: AsyncClient):
    """Test login failure with non-existent user."""
    # Use factory to generate a unique email that won't exist
    nonexistent_user = create_test_user()

    response = await async_client.post(
        "/api/v1/login/access-token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": nonexistent_user.email, "password": "testpass123"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Incorrect email or password"
