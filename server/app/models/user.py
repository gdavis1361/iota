from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.password import get_password_hash, verify_password
from app.db.base_class import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(Base):
    """User model."""

    __tablename__ = "users"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)

    # Status flags
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    role = Column(String, default=UserRole.USER)

    # Timestamps are inherited from Base
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        """Verify password."""
        return verify_password(password, self.hashed_password)

    def change_password(self, password: str) -> None:
        """Change password."""
        self.hashed_password = get_password_hash(password)

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Convert model to dictionary."""
        d = super().dict(*args, **kwargs)
        d.pop("hashed_password", None)  # Don't expose password hash
        return d
