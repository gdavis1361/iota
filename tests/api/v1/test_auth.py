"""Test authentication endpoints."""
import pytest
import pytest_asyncio
import structlog
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.user import User

# Configure logging
logger = structlog.get_logger()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    logger.info("creating_test_user")

    # Create user with known credentials
    password = "testpass123"
    user = User(
        email="test@example.com",
        hashed_password=security.get_password_hash(password),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    logger.info("test_user_created", user_id=user.id, email=user.email)
    return user


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncClient:
    """Create async test client."""
    logger.info("creating_test_client")

    # Override the database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create client with test server host
    async with AsyncClient(app=app, base_url=settings.SERVER_HOST, follow_redirects=True) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()
    logger.info("test_client_cleanup_complete")


@pytest.mark.asyncio
async def test_login_access_token(async_client: AsyncClient, test_user: User):
    """Test login endpoint."""
    logger.info("testing_login_access_token")

    # Test successful login
    data = {"username": test_user.email, "password": "testpass123"}
    response = await async_client.post(f"{settings.API_V1_STR}/auth/access-token", data=data)
    assert response.status_code == 200
    token = response.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"

    # Test invalid password
    data["password"] = "wrong"
    response = await async_client.post(f"{settings.API_V1_STR}/auth/access-token", data=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_inactive_user(async_client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Test login with inactive user."""
    logger.info("testing_inactive_user")

    # Deactivate user
    test_user.is_active = False
    await db_session.flush()
    await db_session.refresh(test_user)

    data = {"username": test_user.email, "password": "testpass123"}
    response = await async_client.post(f"{settings.API_V1_STR}/auth/access-token", data=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, test_user: User):
    """Test login with invalid credentials."""
    logger.info("testing_invalid_credentials")

    # Test with non-existent user
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/access-token",
        data={"username": "nonexistent@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    # Test with wrong password
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/access-token",
        data={"username": test_user.email, "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_malformed_request(async_client: AsyncClient):
    """Test login with malformed request data."""
    logger.info("testing_malformed_request")

    # Missing password
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/access-token", data={"username": "test@example.com"}
    )
    assert response.status_code == 422
    logger.info("missing_password_rejected")

    # Missing username
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/access-token", data={"password": "testpass123"}
    )
    assert response.status_code == 422
    logger.info("missing_username_rejected")

    # Empty credentials
    response = await async_client.post(f"{settings.API_V1_STR}/auth/access-token", data={})
    assert response.status_code == 422
    logger.info("empty_credentials_rejected")


@pytest.mark.asyncio
async def test_token_validation(async_client: AsyncClient, test_user: User):
    """Test token validation endpoint."""
    logger.info("testing_token_validation")

    # Get valid token
    data = {"username": test_user.email, "password": "testpass123"}
    response = await async_client.post(f"{settings.API_V1_STR}/auth/access-token", data=data)
    token = response.json()["access_token"]

    # Test valid token
    response = await async_client.get(
        f"{settings.API_V1_STR}/auth/verify", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == test_user.email

    # Test invalid token
    response = await async_client.get(
        f"{settings.API_V1_STR}/auth/verify", headers={"Authorization": "Bearer invalid"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
