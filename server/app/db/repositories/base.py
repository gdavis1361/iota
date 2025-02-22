from __future__ import annotations

from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar, Union, cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Result, ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
IdType = Union[int, str, UUID]  # Common ID types


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common database operations
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: IdType) -> Optional[ModelType]:
        """Get a single record by id"""
        query = select(self.model).where(self.model.id == id)
        result: Result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by(self, **kwargs: Any) -> Optional[ModelType]:
        """Get a single record by arbitrary filters"""
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(self.model).where(*filters)
        result: Result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get a list of records with pagination"""
        query = select(self.model).offset(skip).limit(limit)
        result: ScalarResult = await self.session.scalars(query)
        return list(result.all())

    async def list_by(self, skip: int = 0, limit: int = 100, **kwargs: Any) -> List[ModelType]:
        """Get a list of records with filters and pagination"""
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(self.model).where(*filters).offset(skip).limit(limit)
        result: ScalarResult = await self.session.scalars(query)
        return list(result.all())

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return cast(ModelType, db_obj)

    async def update(self, id: IdType, **kwargs: Any) -> Optional[ModelType]:
        """Update a record by id"""
        query = update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)
        result = await self.session.execute(query)
        await self.session.commit()
        return cast(Optional[ModelType], result.scalar_one_or_none())

    async def delete(self, id: IdType) -> bool:
        """Delete a record by id"""
        query = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        await self.session.commit()
        return bool(result.rowcount > 0 if result.rowcount is not None else False)

    async def count(self, **kwargs: Any) -> int:
        """Count records with optional filters"""
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(func.count()).select_from(self.model).where(*filters)
        result = await self.session.scalar(query)
        return result or 0
