from datetime import datetime, timedelta
from typing import Any, Union, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload
from app.core.password import verify_password, get_password_hash
from app.core.logging_config import diagnostics

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # If subject is a dict, use it directly, otherwise create a sub claim
    if isinstance(subject, dict):
        to_encode = {"exp": expire, **subject}
    else:
        to_encode = {"exp": expire, "sub": str(subject)}
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # If subject is a dict, use it directly, otherwise create a sub claim
    if isinstance(subject, dict):
        to_encode = {"exp": expire, "type": "refresh", **subject}
    else:
        to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieve a user from the database by their email address.

    Args:
        db (Session): The database session used for querying.
        email (str): The email address of the user.

    Returns:
        Optional[User]: The user object if found, else None.
    """
    return db.query(User).filter(User.email == email).first()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    diagnostics.loggers['security'].info("Extracting token using oauth2_scheme")
    try:
        diagnostics.loggers['security'].info("Decoding token using jwt.decode")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        diagnostics.loggers['security'].info("Constructing TokenPayload and checking 'sub' field")
        email: str = payload.get("sub")
        if email is None:
            diagnostics.loggers['security'].warning("Token 'sub' field is None, raising credentials_exception")
            raise credentials_exception
        
        diagnostics.loggers['security'].info(f"Retrieving user by email: {email}")
        user = get_user_by_email(db, email)
        
        if user is None:
            diagnostics.loggers['security'].warning("User not found, raising credentials_exception")
            raise credentials_exception
    except JWTError as e:
        diagnostics.loggers['security'].error(f"JWTError occurred: {str(e)}")
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user using their email and password.
    
    Args:
        db (Session): Database session for querying.
        email (str): The user's email address.
        password (str): The plaintext password provided by the user.
    
    Returns:
        Optional[User]: The user object if authentication is successful, else None.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
