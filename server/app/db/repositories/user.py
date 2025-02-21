from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from app.models.enums import UserRole

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_in: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user_in.password)
        user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            is_active=True,
            is_verified=False,
            is_superuser=False,
            role=UserRole.USER
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: int) -> Optional[User]:
        """Get user by id"""
        result = await self.db.execute(
            select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def update(self, user: User, user_in: UserUpdate) -> User:
        """Update user"""
        update_data = user_in.model_dump(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        # Update all fields in the database
        update_stmt = update(User).where(User.id == user.id)
        update_values = {}
        
        # Always include all fields in the update
        update_values["full_name"] = update_data.get("full_name", user.full_name)
        update_values["is_active"] = bool(update_data.get("is_active", user.is_active))
        update_values["is_verified"] = bool(update_data.get("is_verified", user.is_verified))
        update_values["role"] = UserRole(update_data["role"]) if "role" in update_data else user.role
        if "hashed_password" in update_data:
            update_values["hashed_password"] = update_data["hashed_password"]
        
        update_values["updated_at"] = datetime.utcnow()
        await self.db.execute(update_stmt.values(**update_values))
        await self.db.commit()
        
        # Refresh and return the updated user
        return await self.get_by_id(user.id)

    async def delete(self, user_id: int) -> Optional[User]:
        """Delete user"""
        user = await self.get_by_id(user_id)
        if user:
            await self.db.execute(delete(User).where(User.id == user_id))
            await self.db.commit()
        return user

    async def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users"""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()
