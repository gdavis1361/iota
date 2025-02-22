"""User management endpoints."""
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.error_handlers import APIError
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

# Configure structured logging
logger = structlog.get_logger()

router = APIRouter()


@router.post("", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create new user.

    Args:
        user_in: User creation data
        db: Database session

    Returns:
        Created user
    """
    # Create new user
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=True,
    )
    db.add(db_user)

    # Commit transaction
    await db.commit()
    await db.refresh(db_user)

    # Log success and return
    logger.info(
        "user_created",
        user_id=db_user.id,
        email=db_user.email,
    )
    return db_user
