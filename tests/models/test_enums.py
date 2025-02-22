"""Test enum functionality."""
import json

import pytest
from pydantic import BaseModel

from app.models.enums import UserRole


def test_user_role_values():
    """Test UserRole enum values."""
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserRole.USER.value == "USER"

    # Verify all values are strings
    for role in UserRole:
        assert isinstance(role.value, str)


def test_user_role_comparison():
    """Test UserRole comparison functionality."""
    # Direct comparison
    assert UserRole.ADMIN == UserRole.ADMIN
    assert UserRole.ADMIN != UserRole.USER

    # String comparison (important for API handling)
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.USER == "USER"
    assert UserRole.ADMIN != "USER"


def test_user_role_serialization():
    """Test UserRole serialization behavior."""
    # JSON serialization
    assert json.dumps(UserRole.ADMIN.value) == '"ADMIN"'

    # Dict conversion
    role_dict = {"role": UserRole.ADMIN}
    assert role_dict["role"] == UserRole.ADMIN
    assert role_dict["role"].value == "ADMIN"


def test_user_role_pydantic_integration():
    """Test UserRole works with Pydantic models."""

    class UserModel(BaseModel):
        role: UserRole

    # Create from enum
    user = UserModel(role=UserRole.ADMIN)
    assert user.role == UserRole.ADMIN

    # Create from string
    user = UserModel(role="USER")
    assert user.role == UserRole.USER

    # Invalid role should raise error
    with pytest.raises(ValueError):
        UserModel(role="INVALID")


def test_user_role_iteration():
    """Test UserRole can be iterated."""
    roles = list(UserRole)
    assert len(roles) == 3  # ADMIN, USER, GUEST
    assert UserRole.ADMIN in roles
    assert UserRole.USER in roles
    assert UserRole.GUEST in roles


def test_user_role_string_conversion():
    """Test UserRole string conversion."""
    assert str(UserRole.ADMIN) == "UserRole.ADMIN"
    assert str(UserRole.USER) == "UserRole.USER"

    # Value property gives raw string
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserRole.USER.value == "USER"

    # Verify repr
    assert repr(UserRole.ADMIN) == "<UserRole.ADMIN: 'ADMIN'>"
    assert repr(UserRole.USER) == "<UserRole.USER: 'USER'>"
