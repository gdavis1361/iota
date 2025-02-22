"""Test cases for user management endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.tests.utils.utils import random_email, random_lower_string

client = TestClient(app)


def test_read_users_superuser(db: Session) -> None:
    """Test reading users list as superuser."""
    # Create test user
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(user.id)
    response = client.get(
        f"{settings.API_V1_STR}/users/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content) >= 1
    assert content[0]["email"] == email


def test_read_users_normal_user(db: Session) -> None:
    """Test reading users list as normal user."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(user.id)
    response = client.get(
        f"{settings.API_V1_STR}/users/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_create_user_superuser(db: Session) -> None:
    """Test user creation by superuser."""
    # Create superuser
    admin_email = random_email()
    admin_password = random_lower_string()
    admin = User(
        email=admin_email,
        hashed_password=security.get_password_hash(admin_password),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()

    access_token = create_access_token(admin.id)
    data = {
        "email": random_email(),
        "password": random_lower_string(),
        "full_name": random_lower_string(),
        "is_active": True,
        "is_superuser": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == data["email"]
    assert content["is_active"] == data["is_active"]
    assert content["is_superuser"] == data["is_superuser"]
    assert "id" in content


def test_create_user_normal_user(db: Session) -> None:
    """Test user creation by normal user."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(user.id)
    data = {
        "email": random_email(),
        "password": random_lower_string(),
        "full_name": random_lower_string(),
    }
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=data,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_read_user_me(db: Session) -> None:
    """Test reading own user data."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(user.id)
    response = client.get(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == email
    assert content["id"] == user.id


def test_read_user_unauthorized(db: Session) -> None:
    """Test reading other user's data without permission."""
    # Create first user
    email1 = random_email()
    password1 = random_lower_string()
    user1 = User(
        email=email1,
        hashed_password=security.get_password_hash(password1),
        is_active=True,
    )
    db.add(user1)

    # Create second user
    email2 = random_email()
    password2 = random_lower_string()
    user2 = User(
        email=email2,
        hashed_password=security.get_password_hash(password2),
        is_active=True,
    )
    db.add(user2)
    db.commit()

    access_token = create_access_token(user1.id)
    response = client.get(
        f"{settings.API_V1_STR}/users/{user2.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_update_user_me(db: Session) -> None:
    """Test updating own user data."""
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(user.id)
    new_name = random_lower_string()
    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"full_name": new_name},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["full_name"] == new_name


def test_update_user_superuser(db: Session) -> None:
    """Test updating user data as superuser."""
    # Create normal user
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
    )
    db.add(user)

    # Create superuser
    admin_email = random_email()
    admin_password = random_lower_string()
    admin = User(
        email=admin_email,
        hashed_password=security.get_password_hash(admin_password),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()

    access_token = create_access_token(admin.id)
    data = {
        "is_active": False,
        "is_superuser": True,
    }
    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["is_active"] == data["is_active"]
    assert content["is_superuser"] == data["is_superuser"]


def test_delete_user(db: Session) -> None:
    """Test user deletion by superuser."""
    # Create user to delete
    email = random_email()
    password = random_lower_string()
    user = User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_active=True,
    )
    db.add(user)

    # Create superuser
    admin_email = random_email()
    admin_password = random_lower_string()
    admin = User(
        email=admin_email,
        hashed_password=security.get_password_hash(admin_password),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()

    access_token = create_access_token(admin.id)
    response = client.delete(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    # Verify user is deleted
    deleted_user = db.query(User).filter(User.id == user.id).first()
    assert not deleted_user
