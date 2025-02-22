from datetime import datetime
from enum import Enum

from app.core.password import get_password_hash, verify_password
from app.db.base import BaseModel
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(BaseModel):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        # Set default values
        self.is_active = True
        self.is_verified = False
        self.is_superuser = False
        self.role = UserRole.USER
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        if "password" in kwargs:
            kwargs["hashed_password"] = get_password_hash(kwargs.pop("password"))
        super().__init__(**kwargs)

    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password."""
        return verify_password(password, self.hashed_password)
