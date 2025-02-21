from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common database operations
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """Get a single record by id"""
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by(self, **kwargs) -> Optional[ModelType]:
        """Get a single record by arbitrary filters"""
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(self.model).where(*filters)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get a list of records with pagination"""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def list_by(self, skip: int = 0, limit: int = 100, **kwargs) -> List[ModelType]:
        """Get a list of records with filters and pagination"""
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(self.model).where(*filters).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update a record by id"""
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, id: Any) -> bool:
        """Delete a record by id"""
        query = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def count(self, **kwargs) -> int:
        """Count records with optional filters"""
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(self.model).where(*filters)
        result = await self.session.execute(query)
        return len(result.scalars().all())
    
    async def exists(self, **kwargs) -> bool:
        """Check if a record exists with given filters"""
        return await self.count(**kwargs) > 0
