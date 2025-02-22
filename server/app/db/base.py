from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, MetaData, event
from sqlalchemy.ext.declarative import as_declarative, declared_attr

# Convention for constraint naming
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


@as_declarative()
class Base:
    """Base class for all database models."""

    metadata = metadata

    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name automatically."""
        return cls.__name__.lower()


class BaseModel(Base):
    """Adds created_at and updated_at columns to models."""

    __abstract__ = True

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    @staticmethod
    def _updated_at(mapper: Any, connection: Any, target: Any) -> None:
        """Update updated_at column on update."""
        target.updated_at = datetime.utcnow()

    @classmethod
    def __declare_last__(cls) -> None:
        """Set up before_update listener."""
        event.listen(cls, "before_update", cls._updated_at)

    def dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update(self, **kwargs: Any) -> None:
        """Update model instance with given kwargs"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


from app.models.audit_log import AuditLog  # noqa
from app.models.refresh_token import RefreshToken  # noqa
from app.models.setting import Setting  # noqa
# Import all models to register them with SQLAlchemy
from app.models.user import User  # noqa
