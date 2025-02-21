from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserToggleActive
from app.db.session import get_db
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve users.
    """
    logger.info(f"Getting users list. Current user: {current_user.email}")
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    users = db.query(User).offset(skip).limit(limit).all()
    logger.info(f"Found {len(users)} users")
    return users

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create new user.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=True,
        password=user_in.password  # This will be hashed in __init__
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/{user_id}/", response_model=UserResponse)
async def get_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get user by ID.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user

@router.put("/{user_id}/", response_model=UserResponse)
async def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a user.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    update_data = user_in.dict(exclude_unset=True)
    if "password" in update_data:
        user.set_password(update_data["password"])
        del update_data["password"]
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    db.delete(user)
    db.commit()
    return None

@router.put("/{user_id}/toggle-active/", response_model=UserResponse)
async def toggle_user_active(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_user),
    toggle_data: UserToggleActive
):
    """
    Toggle user active status.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    user.is_active = toggle_data.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/activity/recent/", response_model=List[dict])
async def get_recent_activity(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent user activity (last 24 hours).
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # For now, we'll just return recent logins based on last_login
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_logins = (
        db.query(User)
        .filter(User.last_login >= yesterday)
        .all()
    )
    
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "activity_type": "login",
            "timestamp": user.last_login.isoformat() if user.last_login else None
        }
        for user in recent_logins
    ]

@router.get("/sessions/active/", response_model=List[dict])
async def get_active_sessions(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get currently active sessions.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # For now, return users who have logged in within the last hour as "active"
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    active_users = (
        db.query(User)
        .filter(User.last_login >= one_hour_ago)
        .all()
    )
    
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "started_at": user.last_login.isoformat() if user.last_login else None
        }
        for user in active_users
    ]
