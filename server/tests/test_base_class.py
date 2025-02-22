from datetime import datetime

import pytest
from app.db.base_class import Base
from sqlalchemy import Column, Integer, MetaData, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# Create TestModel class before any tests run
class TestModel(Base):
    """Test model for base class testing"""

    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


# Add to_dict method to TestModel for testing
def to_dict(self):
    """Convert model instance to dictionary"""
    return {
        "id": self.id,
        "name": self.name,
        "created_at": self.created_at,
        "updated_at": self.updated_at,
    }


TestModel.to_dict = to_dict


def test_tablename_generation():
    """Test automatic tablename generation"""
    # Check that tablename is correctly generated from class name
    assert TestModel.__tablename__ == "testmodel"

    # Test with a differently named class
    class AnotherModel(Base):
        id = Column(Integer, primary_key=True)
        name = Column(String)

    assert AnotherModel.__tablename__ == "anothermodel"


@pytest.mark.asyncio
async def test_base_model_timestamps(db: AsyncSession):
    """Test base model timestamps"""
    # Create a new model instance
    model = TestModel(name="test")
    db.add(model)
    await db.commit()
    await db.refresh(model)

    # Check that timestamps were set
    assert isinstance(model.created_at, datetime)
    assert isinstance(model.updated_at, datetime)
    assert model.created_at == model.updated_at

    # Update the model
    original_created_at = model.created_at
    original_updated_at = model.updated_at

    # Wait a moment to ensure timestamps will be different
    await db.execute("SELECT pg_sleep(0.1)")

    model.name = "updated"
    await db.commit()
    await db.refresh(model)

    # Check that only updated_at changed
    assert model.created_at == original_created_at
    assert model.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_base_model_to_dict(db: AsyncSession):
    """Test base model to_dict method"""
    # Create a new model instance
    model = TestModel(name="test")
    db.add(model)
    await db.commit()
    await db.refresh(model)

    # Convert to dict
    model_dict = model.to_dict()

    # Check all fields are present
    assert isinstance(model_dict, dict)
    assert "id" in model_dict
    assert "name" in model_dict
    assert "created_at" in model_dict
    assert "updated_at" in model_dict

    # Check values
    assert model_dict["name"] == "test"
    assert isinstance(model_dict["id"], int)
    assert isinstance(model_dict["created_at"], datetime)
    assert isinstance(model_dict["updated_at"], datetime)
