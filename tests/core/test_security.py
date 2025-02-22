"""Test security utilities."""
import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password"
    hashed = get_password_hash(password)

    # Verify hash is different from original
    assert hashed != password

    # Verify correct password matches
    assert verify_password(password, hashed)

    # Verify incorrect password doesn't match
    assert not verify_password("wrong_password", hashed)


def test_access_token_creation():
    """Test JWT access token creation."""
    data = {"sub": "test@example.com"}
    token = create_access_token(data)

    # Verify token is a string
    assert isinstance(token, str)

    # Verify token can be decoded
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    # Verify data was preserved
    assert decoded["sub"] == data["sub"]
