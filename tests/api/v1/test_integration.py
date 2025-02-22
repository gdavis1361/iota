"""Integration tests for user management and authentication endpoints."""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async for session in get_db():
        yield session


async def test_create_user_success(client: AsyncClient):
    """Test creating a new user successfully."""
    payload = {
        "email": "testuser@example.com",
        "password": "Secretp@ssw0rd",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

    data = response.json()
    assert "id" in data, "User ID missing in response"
    assert data["email"] == payload["email"], "Email does not match"
    assert data["full_name"] == payload["full_name"], "Full name does not match"
    assert data["is_active"], "User should be active by default"
    assert "created_at" in data, "Created timestamp missing"
    assert "updated_at" in data, "Updated timestamp missing"


async def test_create_user_duplicate_email(client: AsyncClient):
    """Test creating a user with an email that already exists."""
    payload = {
        "email": "testuser@example.com",  # Duplicate email from previous test
        "password": "AnotherSecret1!",
        "full_name": "Another User",
    }
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    data = response.json()
    assert "detail" in data, "Error detail missing in response"


async def test_authenticate_success(client: AsyncClient):
    """Test successful authentication attempt."""
    payload = {
        "username": "testuser@example.com",  # Email is used as username
        "password": "Secretp@ssw0rd",
    }
    response = await client.post("/api/v1/auth/access-token", data=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

    data = response.json()
    assert "access_token" in data, "Access token missing in response"
    assert data["token_type"].lower() == "bearer", "Token type should be 'bearer'"


async def test_authenticate_failure(client: AsyncClient):
    """Test authentication with invalid credentials."""
    payload = {"username": "testuser@example.com", "password": "wrongpassword"}
    response = await client.post("/api/v1/auth/access-token", data=payload)
    assert response.status_code == 401, f"Expected status code 401, got {response.status_code}"
    data = response.json()
    assert "detail" in data, "Error detail missing in response"


async def test_create_user_invalid_email(client: AsyncClient):
    """Test creating a user with invalid email format."""
    payload = {
        "email": "invalid-email",
        "password": "Secretp@ssw0rd",
        "full_name": "Invalid Email User",
    }
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    assert "detail" in data, "Validation error details missing"


async def test_create_user_missing_password(client: AsyncClient):
    """Test creating a user without password."""
    payload = {"email": "nopassword@example.com", "full_name": "No Password User"}
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    assert "detail" in data, "Validation error details missing"


async def test_user_lifecycle(client: AsyncClient):
    """Test complete user lifecycle including creation and authentication."""
    # 1. Create user
    create_payload = {
        "email": "lifecycle@example.com",
        "password": "Lifecyclep@ss123",
        "full_name": "Lifecycle Test",
    }
    create_response = await client.post("/api/v1/users", json=create_payload)
    assert create_response.status_code == 200
    user_data = create_response.json()

    # 2. Authenticate
    auth_payload = {"username": create_payload["email"], "password": create_payload["password"]}
    auth_response = await client.post("/api/v1/auth/access-token", data=auth_payload)
    assert auth_response.status_code == 200
    token_data = auth_response.json()

    # 3. Verify token structure
    assert "access_token" in token_data
    assert token_data["token_type"].lower() == "bearer"

    # 4. Try invalid password
    invalid_auth = {"username": create_payload["email"], "password": "wrong_password"}
    invalid_response = await client.post("/api/v1/auth/access-token", data=invalid_auth)
    assert invalid_response.status_code == 401
