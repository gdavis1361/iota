"""Test base model functionality."""
import asyncio
import datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import Column, String, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base, BaseModel
from tests.utils.utils import verify_tables_exist


class TestModel(BaseModel):
    """Test model for base functionality."""

    __tablename__ = "test_models"
    name = Column(String, nullable=False)


@pytest_asyncio.fixture
async def test_model(async_session: AsyncSession) -> AsyncGenerator[TestModel, None]:
    """Create a test model instance."""
    model = TestModel(name="test")
    async_session.add(model)
    await async_session.flush()
    yield model


@pytest.mark.asyncio
async def test_convention_naming(async_session: AsyncSession):
    """Test naming conventions are applied correctly."""
    # Verify table exists
    await verify_tables_exist(async_session, ["test_models"])

    # Get primary key constraint name
    result = await async_session.execute(
        text(
            """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'test_models'
        AND constraint_type = 'PRIMARY KEY'
        """
        )
    )
    pk_name = result.scalar()
    assert pk_name == "pk_test_models"


@pytest.mark.asyncio
async def test_base_model_instantiation(test_model: TestModel):
    """Test base model instantiation."""
    assert isinstance(test_model, BaseModel)
    assert isinstance(test_model, Base)
    assert test_model.name == "test"
    assert test_model.id is not None  # Already persisted


@pytest.mark.asyncio
async def test_common_fields(async_session: AsyncSession):
    """Test common fields are set correctly."""
    # Verify table exists
    await verify_tables_exist(async_session, ["test_models"])

    # Create and persist a model
    model = TestModel(name="test_fields")
    async_session.add(model)
    await async_session.flush()
    await async_session.refresh(model)  # Refresh to ensure all fields are loaded

    # Verify fields are set
    assert model.id is not None
    assert isinstance(model.created_at, datetime.datetime)
    assert isinstance(model.updated_at, datetime.datetime)
    assert model.created_at.tzinfo is not None  # Timezone aware
    assert model.updated_at.tzinfo is not None  # Timezone aware


@pytest.mark.asyncio
async def test_update_timestamp(async_session: AsyncSession):
    """Test updated_at is automatically updated."""
    # Verify table exists
    await verify_tables_exist(async_session, ["test_models"])

    # Create and persist a model
    model = TestModel(name="test_update")
    async_session.add(model)
    await async_session.flush()
    original_updated_at = model.updated_at

    # Wait a moment and update
    await asyncio.sleep(0.1)
    model.name = "updated"
    await async_session.flush()

    # Verify updated_at changed
    assert model.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_dict_conversion(async_session: AsyncSession):
    """Test model to dictionary conversion."""
    # Create a model instance
    model = TestModel(name="test_dict")
    async_session.add(model)
    await async_session.flush()

    # Convert to dictionary
    model_dict = model.dict()

    # Verify dictionary contents
    assert isinstance(model_dict, dict)
    assert model_dict["name"] == "test_dict"
    assert "id" in model_dict
    assert "created_at" in model_dict
    assert "updated_at" in model_dict


@pytest.mark.asyncio
async def test_update_method(async_session: AsyncSession):
    """Test model update method."""
    # Create initial model
    model = TestModel(name="original")
    async_session.add(model)
    await async_session.flush()

    # Update using method
    model.update(name="updated")
    await async_session.flush()

    # Verify changes
    assert model.name == "updated"


@pytest.mark.asyncio
async def test_update_method_invalid_attr(test_model: TestModel):
    """Test update method with invalid attribute."""
    # Update with invalid attribute
    test_model.update(invalid_attr="value")

    # Verify no attribute was added
    assert not hasattr(test_model, "invalid_attr")

    # Update with mix of valid and invalid attributes
    test_model.update(name="updated", invalid_attr="value")
    assert test_model.name == "updated"
    assert not hasattr(test_model, "invalid_attr")


@pytest.mark.asyncio
async def test_dict_conversion_all_fields(async_session: AsyncSession):
    """Test dictionary conversion with all field types."""
    # Create model with all fields set
    model = TestModel(name="test_dict")
    async_session.add(model)
    await async_session.flush()
    await async_session.refresh(model)

    # Convert to dict
    model_dict = model.dict()

    # Verify all fields are present
    assert set(model_dict.keys()) == {"id", "name", "created_at", "updated_at"}

    # Verify field types
    assert isinstance(model_dict["id"], int)
    assert isinstance(model_dict["name"], str)
    assert isinstance(model_dict["created_at"], datetime.datetime)
    assert isinstance(model_dict["updated_at"], datetime.datetime)

    # Verify timezone awareness
    assert model_dict["created_at"].tzinfo is not None
    assert model_dict["updated_at"].tzinfo is not None


@pytest.mark.asyncio
async def test_model_query(async_session: AsyncSession):
    """Test model querying."""
    # Create test data
    model = TestModel(name="query_test")
    async_session.add(model)
    await async_session.flush()

    # Query the model
    result = await async_session.execute(select(TestModel).where(TestModel.name == "query_test"))
    queried_model = result.scalar_one()

    # Verify query result
    assert queried_model.id == model.id
    assert queried_model.name == "query_test"


@pytest.mark.asyncio
async def test_model_cascade_timestamp(async_session: AsyncSession):
    """Test timestamp cascade behavior."""
    # Create and persist a model
    model = TestModel(name="cascade_test")
    async_session.add(model)
    await async_session.flush()

    # Store original timestamps
    created_at = model.created_at
    updated_at = model.updated_at

    # Update through session
    await asyncio.sleep(0.1)
    model.name = "cascaded"
    await async_session.flush()

    # Verify timestamps
    assert model.created_at == created_at  # Should not change
    assert model.updated_at > updated_at  # Should be updated
