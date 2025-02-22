"""Test database initialization and model imports."""
import pytest
from sqlalchemy import inspect

from app.db.init import Base
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.setting import Setting
from app.models.user import User


def test_base_metadata_tables():
    """Test that all models are properly registered with Base.metadata."""
    inspector = inspect(Base.metadata)

    # Expected tables based on our models
    expected_tables = {
        "users",
        "audit_logs",
        "refresh_tokens",
        "settings",
    }

    # Get actual tables from metadata
    actual_tables = set(inspector.tables.keys())

    # Verify all expected tables are present
    assert expected_tables.issubset(
        actual_tables
    ), f"Missing tables. Expected: {expected_tables}, Got: {actual_tables}"


def test_model_relationships():
    """Test that model relationships are properly configured."""
    # Test User relationships
    user_rels = {rel.key: rel for rel in User.__mapper__.relationships}
    assert "refresh_tokens" in user_rels, "User should have refresh_tokens relationship"

    # Test RefreshToken relationships
    token_rels = {rel.key: rel for rel in RefreshToken.__mapper__.relationships}
    assert "user" in token_rels, "RefreshToken should have user relationship"


def test_model_table_names():
    """Test that models have correct table names."""
    assert User.__tablename__ == "users"
    assert AuditLog.__tablename__ == "audit_logs"
    assert RefreshToken.__tablename__ == "refresh_tokens"
    assert Setting.__tablename__ == "settings"


def test_model_primary_keys():
    """Test that models have properly configured primary keys."""
    for model in [User, AuditLog, RefreshToken, Setting]:
        pk = model.__mapper__.primary_key
        assert len(pk) > 0, f"{model.__name__} should have a primary key"
        assert "id" in [col.name for col in pk], f"{model.__name__} should have 'id' as primary key"


def test_model_common_fields():
    """Test that models inherit common fields from BaseModel."""
    common_fields = {"created_at", "updated_at"}
    for model in [User, AuditLog, RefreshToken, Setting]:
        model_fields = {col.name for col in model.__table__.columns}
        assert common_fields.issubset(
            model_fields
        ), f"{model.__name__} missing common fields: {common_fields - model_fields}"
