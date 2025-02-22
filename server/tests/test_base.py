from datetime import datetime

import pytest
from app.models.base import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession


class TestModel(Base):
    """Test model for base model testing"""

    __tablename__ = "test_models"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


@pytest.mark.asyncio
async def test_base_model_crud(db: AsyncSession):
    """Test base model CRUD operations"""
    # Create
    model = TestModel(name="test")
    db.add(model)
    await db.commit()
    await db.refresh(model)

    assert model.id is not None
    assert model.name == "test"
    assert isinstance(model.created_at, datetime)
    assert isinstance(model.updated_at, datetime)

    # Read
    stmt = await db.execute("SELECT * FROM test_models WHERE id = :id", {"id": model.id})
    result = stmt.fetchone()
    assert result is not None
    assert result.id == model.id
    assert result.name == "test"

    # Update
    original_updated_at = model.updated_at
    await db.execute("SELECT pg_sleep(0.1)")  # Ensure timestamp will be different

    model.name = "updated"
    await db.commit()
    await db.refresh(model)

    assert model.name == "updated"
    assert model.updated_at > original_updated_at
    assert model.created_at < model.updated_at

    # Delete
    await db.delete(model)
    await db.commit()

    stmt = await db.execute("SELECT * FROM test_models WHERE id = :id", {"id": model.id})
    result = stmt.fetchone()
    assert result is None


@pytest.mark.asyncio
async def test_base_model_dict(db: AsyncSession):
    """Test base model dict method"""
    model = TestModel(name="test")
    db.add(model)
    await db.commit()
    await db.refresh(model)

    data = model.to_dict()
    assert isinstance(data, dict)
    assert data["id"] == model.id
    assert data["name"] == "test"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_base_model_update(db: AsyncSession):
    """Test base model update method"""
    model = TestModel(name="test")
    db.add(model)
    await db.commit()
    await db.refresh(model)

    update_data = {"name": "updated"}
    await model.update(db, update_data)

    assert model.name == "updated"

    # Verify in database
    stmt = await db.execute("SELECT * FROM test_models WHERE id = :id", {"id": model.id})
    result = stmt.fetchone()
    assert result is not None
    assert result.name == "updated"
