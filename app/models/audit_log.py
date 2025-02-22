"""Audit log model."""
from sqlalchemy import JSON, Column, String

from app.models.base import BaseModel


class AuditLog(BaseModel):
    """Audit log model."""

    __tablename__ = "audit_logs"

    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    details = Column(JSON)
