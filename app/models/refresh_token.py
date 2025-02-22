"""Refresh token model."""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class RefreshToken(BaseModel):
    """Refresh token model."""

    __tablename__ = "refresh_tokens"

    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", backref="refresh_tokens")
