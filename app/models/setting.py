"""Setting model."""
from sqlalchemy import JSON, Column, String

from app.models.base import BaseModel


class Setting(BaseModel):
    """Setting model."""

    __tablename__ = "settings"

    key = Column(String(255), unique=True, index=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(String(255))
