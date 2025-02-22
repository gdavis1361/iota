from datetime import datetime

from app.models.base import Base
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import Session


class TestModel(Base):
    """Test model for testing Base class functionality"""

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)


def test_tablename_generation():
    """Test automatic tablename generation"""
    assert TestModel.__tablename__ == "testmodel"


def test_common_columns():
    """Test common columns are present"""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session
    session = Session(engine)

    try:
        # Create and add model
        model = TestModel(name="test")
        session.add(model)
        session.flush()  # This triggers the default values

        # Check columns exist
        assert hasattr(model, "id")
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")

        # Check default values
        assert model.id is not None
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

        # Test that updated_at changes on update
        old_updated_at = model.updated_at
        model.name = "updated"
        session.flush()
        assert model.updated_at > old_updated_at
    finally:
        session.close()


def test_dict_method():
    """Test dict() method converts model to dictionary"""
    # Create model with test data
    test_name = "Test Name"
    test_desc = "Test Description"
    model = TestModel(name=test_name, description=test_desc)

    # Convert to dict
    model_dict = model.dict()

    # Check all fields are present
    assert "id" in model_dict
    assert "created_at" in model_dict
    assert "updated_at" in model_dict
    assert "name" in model_dict
    assert "description" in model_dict

    # Check values
    assert model_dict["name"] == test_name
    assert model_dict["description"] == test_desc


def test_update_method():
    """Test update() method updates model attributes"""
    # Create model with initial data
    model = TestModel(name="Initial Name", description="Initial Description")

    # Update with new values
    new_name = "Updated Name"
    new_desc = "Updated Description"
    model.update(name=new_name, description=new_desc)

    # Check values were updated
    assert model.name == new_name
    assert model.description == new_desc

    # Test updating with invalid attribute (should be ignored)
    model.update(invalid_attr="value")
    assert not hasattr(model, "invalid_attr")


def test_update_method_none_value():
    """Test update() method with None values"""
    # Create model with initial data
    model = TestModel(name="Initial Name", description="Initial Description")

    # Update description to None
    model.update(description=None)

    # Check name unchanged and description is None
    assert model.name == "Initial Name"
    assert model.description is None
