from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import settings
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    get_current_user,
    get_password_hash,
    get_user_by_email,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenData
from fastapi import Depends, HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


def test_verify_password():
    """Test password verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_get_password_hash():
    """Test password hashing"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_create_access_token():
    """Test access token creation"""
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    assert isinstance(token, str)

    # Test with expiry
    token = create_access_token(data, expires_delta=timedelta(minutes=30))
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert "exp" in payload


def test_create_refresh_token():
    """Test refresh token creation"""
    data = {"sub": "test@example.com"}
    token = create_refresh_token(data)
    assert isinstance(token, str)

    # Verify token contents
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert payload["type"] == "refresh"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_get_user_by_email(db: AsyncSession):
    """Test getting user by email"""
    # Create a mock user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
    )
    db.add(user)
    await db.commit()

    # Test getting existing user
    found_user = await get_user_by_email(db, "test@example.com")
    assert found_user is not None
    assert found_user.email == "test@example.com"

    # Test getting non-existent user
    not_found_user = await get_user_by_email(db, "nonexistent@example.com")
    assert not_found_user is None


@pytest.mark.asyncio
async def test_authenticate_user(db: AsyncSession):
    """Test user authentication"""
    # Create a test user
    password = "testpassword123"
    user = User(
        email="test@example.com", hashed_password=get_password_hash(password), full_name="Test User"
    )
    db.add(user)
    await db.commit()

    # Test successful authentication
    authenticated_user = await authenticate_user(db, "test@example.com", password)
    assert authenticated_user is not None
    assert authenticated_user.email == "test@example.com"

    # Test wrong password
    wrong_user = await authenticate_user(db, "test@example.com", "wrongpassword")
    assert wrong_user is None

    # Test non-existent user
    nonexistent_user = await authenticate_user(db, "nonexistent@example.com", password)
    assert nonexistent_user is None


@pytest.mark.asyncio
async def test_get_current_user(db: AsyncSession):
    """Test getting current user from token"""
    # Create a test user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
    )
    db.add(user)
    await db.commit()

    # Create a valid token
    token = create_access_token({"sub": user.email})
    current_user = await get_current_user(token, db)
    assert current_user.email == user.email

    # Test invalid token
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("invalid_token", db)
    assert exc_info.value.status_code == 401

    # Test token with missing sub claim
    invalid_token = create_access_token({"not_sub": "test@example.com"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(invalid_token, db)
    assert exc_info.value.status_code == 401

    # Test token with non-existent user
    nonexistent_token = create_access_token({"sub": "nonexistent@example.com"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(nonexistent_token, db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_active_user():
    """Test getting current active user"""
    # Test active user
    active_user = User(
        email="active@example.com",
        hashed_password="hashed",
        full_name="Active User",
        is_active=True,
    )
    current_user = await get_current_active_user(active_user)
    assert current_user == active_user

    # Test inactive user
    inactive_user = User(
        email="inactive@example.com",
        hashed_password="hashed",
        full_name="Inactive User",
        is_active=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(inactive_user)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Inactive user"


@pytest.mark.asyncio
async def test_missing_token(db: Session = Depends(get_db)):
    """Test get_current_user with missing token"""
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(db=db, token="")
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(db: Session = Depends(get_db)):
    """Test get_current_user with invalid token"""
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(db=db, token="invalid_token")
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_non_existent_user(db: Session = Depends(get_db)):
    """Test get_current_user with valid token but non-existent user"""
    # Assuming 'valid_token_for_non_existent_user' is a valid token for a user ID that doesn't exist
    valid_token_for_non_existent_user = "valid_token_for_non_existent_user"
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(db=db, token=valid_token_for_non_existent_user)
    assert excinfo.value.status_code == 401
