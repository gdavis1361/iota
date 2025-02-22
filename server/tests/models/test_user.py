from datetime import datetime

import pytest
from app.core.password import verify_password
from app.models.user import User, UserRole
from app.schemas.user import PasswordChange, UserCreate, UserUpdate


@pytest.fixture
def valid_user_data():
    return {
        "email": "test@example.com",
        "password": "TestPass123",
        "full_name": "Test User",
        "role": UserRole.USER,
    }


@pytest.fixture
def valid_user_create_data():
    return {
        "email": "test@example.com",
        "password": "TestPass123",
        "confirm_password": "TestPass123",
        "full_name": "Test User",
        "role": "USER",
    }


class TestUserModel:
    def test_create_user(self, valid_user_data):
        """Test creating a user with valid data."""
        user = User(**valid_user_data)
        assert user.email == valid_user_data["email"]
        assert user.full_name == valid_user_data["full_name"]
        assert user.role == valid_user_data["role"]
        assert user.is_active is True  # Default value
        assert user.is_verified is False  # Default value
        assert user.is_superuser is False  # Default value
        assert verify_password(valid_user_data["password"], user.hashed_password)

    def test_verify_password(self, valid_user_data):
        """Test password verification."""
        user = User(**valid_user_data)
        assert user.verify_password(valid_user_data["password"]) is True
        assert user.verify_password("wrong_password") is False

    def test_timestamps(self, valid_user_data):
        """Test that timestamps are set correctly."""
        user = User(**valid_user_data)
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        assert user.last_login is None


class TestUserSchemas:
    def test_valid_user_create(self, valid_user_create_data):
        """Test UserCreate schema with valid data."""
        user_create = UserCreate(**valid_user_create_data)
        assert user_create.email == valid_user_create_data["email"]
        assert user_create.password == valid_user_create_data["password"]
        assert user_create.full_name == valid_user_create_data["full_name"]
        assert user_create.role == valid_user_create_data["role"]

    @pytest.mark.parametrize(
        "invalid_email",
        ["not_an_email", "missing@tld", "@missing_local.com", "spaces in@email.com"],
    )
    def test_invalid_email(self, valid_user_create_data, invalid_email):
        """Test that invalid emails are rejected."""
        data = valid_user_create_data.copy()
        data["email"] = invalid_email
        with pytest.raises(ValueError):
            UserCreate(**data)

    @pytest.mark.parametrize(
        "invalid_password",
        [
            "short",  # Too short
            "onlylowercase123",  # No uppercase
            "ONLYUPPERCASE123",  # No lowercase
            "NoNumbers",  # No numbers
            "Ab1",  # Too short with all required chars
        ],
    )
    def test_invalid_password(self, valid_user_create_data, invalid_password):
        """Test that invalid passwords are rejected."""
        data = valid_user_create_data.copy()
        data["password"] = invalid_password
        data["confirm_password"] = invalid_password
        with pytest.raises(ValueError):
            UserCreate(**data)

    def test_password_mismatch(self, valid_user_create_data):
        """Test that mismatched passwords are rejected."""
        data = valid_user_create_data.copy()
        data["confirm_password"] = "DifferentPass123"
        with pytest.raises(ValueError):
            UserCreate(**data)

    def test_invalid_role(self, valid_user_create_data):
        """Test that invalid roles are rejected."""
        data = valid_user_create_data.copy()
        data["role"] = "INVALID_ROLE"
        with pytest.raises(ValueError):
            UserCreate(**data)

    def test_password_change_validation(self):
        """Test password change validation."""
        data = {
            "current_password": "OldPass123",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123",
        }
        password_change = PasswordChange(**data)
        assert password_change.current_password == data["current_password"]
        assert password_change.new_password == data["new_password"]

        # Test password mismatch
        data["confirm_password"] = "DifferentPass123"
        with pytest.raises(ValueError):
            PasswordChange(**data)
