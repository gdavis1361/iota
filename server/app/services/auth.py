from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    SecurityError,
)
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate, PasswordReset
from jose import jwt, JWTError
from app.core.config import settings

class AuthenticationError(SecurityError):
    """Authentication error"""
    pass

class AuthorizationError(SecurityError):
    """Authorization error"""
    pass

class AuthService:
    """Service for handling authentication and authorization"""
    
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if user exists
        if self.user_repo.get_by_email(user_data.email):
            raise AuthenticationError("Email already registered")
        
        # Create user
        user = self.user_repo.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
        
        return user
    
    def get_current_user(self, token: str) -> User:
        try:
            # Remove "Bearer " prefix if present
            if token.startswith("Bearer "):
                token = token.replace("Bearer ", "")
            
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email = payload.get("sub")
            if email is None:
                raise AuthenticationError("Could not validate credentials")
            
            user = self.user_repo.get_by_email(email)
            if not user:
                raise AuthenticationError("User not found")
            
            if not user.is_active:
                raise AuthenticationError("Inactive user")
            
            return user
        except JWTError:
            raise AuthenticationError("Could not validate credentials")
    
    def create_tokens(self, user: User) -> Tuple[str, str]:
        """Create access and refresh tokens for user"""
        access_token = create_access_token({"sub": user.email})
        refresh_token = create_refresh_token({"sub": user.email})
        return access_token, refresh_token
    
    def refresh_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token"""
        payload = verify_token(refresh_token, refresh=True)
        if not payload:
            raise AuthenticationError("Invalid refresh token")
        
        user = self.user_repo.get_by_email(payload.get("sub"))
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("Inactive user")
        
        return create_access_token({"sub": user.email})
