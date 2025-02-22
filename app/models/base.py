"""Base model for all database models."""
import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, MetaData
from sqlalchemy.ext.declarative import declarative_base

# Naming convention for constraints and indexes
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=NAMING_CONVENTION)

# Create declarative base
Base = declarative_base(metadata=metadata)


def utcnow_with_tz() -> datetime.datetime:
    """Get current UTC time with timezone info."""
    return datetime.datetime.now(datetime.timezone.utc)


class BaseModel(Base):
    """Base model with common fields and functionality."""

    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=utcnow_with_tz, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow_with_tz, onupdate=utcnow_with_tz, nullable=False
    )

    def dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update(self, **kwargs: Any) -> None:
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
