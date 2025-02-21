from fastapi.testclient import TestClient
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserCreate
from app.db.repositories.user import UserRepository
from app.main import app

@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user"""
    user_repo = UserRepository(db)
    user_in = UserCreate(
        email="test@example.com",
        password="testpassword123",
        confirm_password="testpassword123",
        full_name="Test User"
    )
    user = await user_repo.create(user_in)
    return user

@pytest.fixture
async def auth_headers(test_user: User) -> dict:
    """Create authentication headers"""
    test_user = test_user  # Remove await as test_user is not a coroutine
    access_token = create_access_token({"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_read_users_me(client, auth_headers):
    """Test getting current user profile"""
    response = await client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data

@pytest.mark.asyncio
async def test_update_user_me(client, auth_headers):
    """Test updating user profile"""
    update_data = {"full_name": "Updated Name"}
    response = await client.put("/api/v1/users/me", headers=auth_headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test accessing protected endpoint without token"""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Test accessing with invalid token"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_root_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to JSquared API",
        "version": "1.0.0",
        "docs_url": "/api/v1/docs"
    }

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client):
    response = await client.get("/api/v1/protected-endpoint")
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_error_handling(client):
    response = await client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    assert "detail" in response.json()
    assert response.json()["detail"] == "Not Found"

@pytest.mark.asyncio
async def test_performance(client):
    response = await client.get("/")
    assert response.elapsed.total_seconds() < 0.5
