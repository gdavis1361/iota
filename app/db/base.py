"""Base module for database models.

Import all models here to ensure they are registered with SQLAlchemy metadata
before creating tables.
"""
from app.models.audit_log import AuditLog  # noqa
from app.models.base import Base  # noqa
from app.models.refresh_token import RefreshToken  # noqa
from app.models.setting import Setting  # noqa
from app.models.user import User  # noqa
