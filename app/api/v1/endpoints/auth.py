"""Authentication endpoints."""
from datetime import timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# Configure structured logging
logger = structlog.get_logger()

router = APIRouter()


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str


class TokenInfo(BaseModel):
    """Token validation response model."""

    email: str
    is_active: bool


@router.post("/access-token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """OAuth2 compatible token login, get an access token for future requests."""
    try:
        # Attempt to authenticate user
        logger.info("login_attempt", username=form_data.username, scopes=form_data.scopes)

        # Check if user exists and is active
        result = await db.execute(select(User).where(User.email == form_data.username))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("login_failed", reason="user_not_found", username=form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        if not security.verify_password(form_data.password, user.hashed_password):
            logger.warning("login_failed", reason="invalid_password", user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        if not user.is_active:
            logger.warning("login_failed", reason="inactive_user", user_id=user.id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

        # Generate access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(user.id, expires_delta=access_token_expires)

        logger.info(
            "login_successful",
            user_id=user.id,
            token_expires_in=access_token_expires.total_seconds(),
        )

        return Token(access_token=access_token, token_type="bearer")

    except Exception as e:
        logger.error("login_error", error=str(e), username=form_data.username)
        raise


@router.get("/verify", response_model=TokenInfo)
async def verify_token(
    current_user: User = Depends(security.get_current_user),
) -> TokenInfo:
    """Verify access token and return token info if valid."""
    return TokenInfo(email=current_user.email, is_active=current_user.is_active)
