from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class RefreshToken(Base):
    """Refresh token model."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(Integer, nullable=False)
    revoked = Column(Integer, default=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
