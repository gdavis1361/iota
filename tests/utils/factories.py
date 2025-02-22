"""Test data factories.

This module provides factory functions for generating test data across different models.
Using factories helps ensure:
1. Test data isolation through unique identifiers
2. Consistent data generation patterns
3. Reduced code duplication
4. Easy customization of test scenarios

Example usage:
    # Create a basic test user
    user = create_test_user()

    # Create a user with custom attributes
    admin = create_test_user(
        email="admin@example.com",
        is_active=True,
        full_name="Admin User"
    )

    # Create a refresh token for testing
    token = create_test_refresh_token(user_id=user.id)

    # Create an audit log entry
    log = create_test_audit_log(
        user_id=user.id,
        action="user.login"
    )

    # Create a setting
    setting = create_test_setting(
        key="rate_limit",
        value={"requests_per_minute": 60}
    )
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.setting import Setting
from app.models.user import User


def create_test_user(
    *,
    email: Optional[str] = None,
    password: str = "testpass123",
    is_active: bool = True,
    full_name: Optional[str] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> User:
    """Create a test user with unique email.

    Args:
        email: Optional email address. If not provided, generates a unique one.
        password: Password for the user. Defaults to 'testpass123'.
        is_active: Whether the user is active. Defaults to True.
        full_name: Optional full name for the user.
        created_at: Optional creation timestamp. Defaults to current time.
        updated_at: Optional update timestamp. Defaults to current time.

    Returns:
        User: A new User instance with the specified or generated attributes.

    Examples:
        # Create a basic active user
        user = create_test_user()

        # Create an inactive user with custom email
        inactive = create_test_user(
            email="inactive@example.com",
            is_active=False
        )

        # Create a user with all custom attributes
        custom = create_test_user(
            email="custom@example.com",
            password="custom123",
            is_active=True,
            full_name="Custom User",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        )
    """
    if email is None:
        # Generate unique email if none provided
        unique_id = str(uuid.uuid4())[:8]
        email = f"test-{unique_id}@example.com"

    now = datetime.now(timezone.utc)
    return User(
        email=email,
        hashed_password=get_password_hash(password),
        is_active=is_active,
        full_name=full_name,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def create_test_refresh_token(
    *,
    user_id: int,
    token: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    is_valid: bool = True,
    created_at: Optional[datetime] = None,
) -> RefreshToken:
    """Create a test refresh token.

    Args:
        user_id: ID of the user this token belongs to
        token: Optional token string. If not provided, generates a unique one.
        expires_at: Optional expiration time. Defaults to 30 days from now.
        is_valid: Whether the token is valid. Defaults to True.
        created_at: Optional creation timestamp. Defaults to current time.

    Returns:
        RefreshToken: A new RefreshToken instance.

    Examples:
        # Create a basic valid token
        token = create_test_refresh_token(user_id=1)

        # Create an expired token
        expired = create_test_refresh_token(
            user_id=1,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        # Create an invalid token
        invalid = create_test_refresh_token(
            user_id=1,
            is_valid=False
        )
    """
    if token is None:
        token = str(uuid.uuid4())

    now = datetime.now(timezone.utc)
    if expires_at is None:
        # Default to 30 days from now
        expires_at = now + timedelta(days=30)

    return RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        is_valid=is_valid,
        created_at=created_at or now,
    )


def create_test_audit_log(
    *,
    user_id: int,
    action: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    created_at: Optional[datetime] = None,
) -> AuditLog:
    """Create a test audit log entry.

    Args:
        user_id: ID of the user who performed the action
        action: The action performed (e.g., 'user.login')
        resource_id: Optional ID of the resource affected
        details: Optional dictionary of additional details
        created_at: Optional creation timestamp. Defaults to current time.

    Returns:
        AuditLog: A new AuditLog instance.

    Examples:
        # Create a basic login log
        log = create_test_audit_log(
            user_id=1,
            action="user.login"
        )

        # Create a detailed action log
        detailed = create_test_audit_log(
            user_id=1,
            action="setting.update",
            resource_id="rate_limit",
            details={"old": 60, "new": 100}
        )
    """
    if details is None:
        details = {}

    now = datetime.now(timezone.utc)
    return AuditLog(
        user_id=user_id,
        action=action,
        resource_id=resource_id,
        details=details,
        created_at=created_at or now,
    )


def create_test_setting(
    *,
    key: str,
    value: Union[str, int, float, bool, dict, list],
    description: Optional[str] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> Setting:
    """Create a test setting.

    Args:
        key: The setting key (e.g., 'rate_limit')
        value: The setting value, can be any JSON-serializable type
        description: Optional description of the setting
        created_at: Optional creation timestamp. Defaults to current time.
        updated_at: Optional update timestamp. Defaults to current time.

    Returns:
        Setting: A new Setting instance.

    Examples:
        # Create a simple numeric setting
        rate_limit = create_test_setting(
            key="rate_limit",
            value=60
        )

        # Create a complex setting with nested data
        email_config = create_test_setting(
            key="email_settings",
            value={
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "use_tls": True
            },
            description="Email server configuration"
        )

        # Create a feature flag
        feature = create_test_setting(
            key="feature_dark_mode",
            value=True,
            description="Enable dark mode UI"
        )
    """
    now = datetime.now(timezone.utc)
    return Setting(
        key=key,
        value=value,
        description=description,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
