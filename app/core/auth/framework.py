"""Comprehensive authentication framework."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import record_metric
from app.core.redis.connection_manager import redis_manager
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.token import TokenPayload

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Authentication related errors."""

    pass


class SessionStore:
    """Manages user sessions with Redis backend."""

    def __init__(self):
        self.prefix = "session:"
        self.token_prefix = "token:"

    async def create_session(self, user_id: int, token: str) -> None:
        """Create a new session."""
        try:
            session_key = f"{self.prefix}{user_id}"
            token_key = f"{self.token_prefix}{token}"

            async with redis_manager.connection() as redis:
                # Store session data
                await redis.hset(
                    session_key,
                    mapping={
                        "token": token,
                        "created_at": datetime.utcnow().isoformat(),
                        "last_active": datetime.utcnow().isoformat(),
                    },
                )
                # Set token to user_id mapping
                await redis.set(
                    token_key, str(user_id), ex=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                )

            record_metric("auth.session.create.success", 1)
        except Exception as e:
            record_metric("auth.session.create.failure", 1)
            logger.error(f"Failed to create session: {str(e)}")
            raise AuthenticationError("Session creation failed")

    async def validate_session(self, token: str) -> Optional[int]:
        """Validate a session token."""
        try:
            token_key = f"{self.token_prefix}{token}"

            async with redis_manager.connection() as redis:
                user_id = await redis.get(token_key)
                if not user_id:
                    return None

                # Update last active
                session_key = f"{self.prefix}{user_id}"
                await redis.hset(session_key, "last_active", datetime.utcnow().isoformat())

            record_metric("auth.session.validate.success", 1)
            return int(user_id)
        except Exception as e:
            record_metric("auth.session.validate.failure", 1)
            logger.error(f"Failed to validate session: {str(e)}")
            return None

    async def invalidate_session(self, user_id: int) -> None:
        """Invalidate all sessions for a user."""
        try:
            session_key = f"{self.prefix}{user_id}"

            async with redis_manager.connection() as redis:
                # Get current token
                token = await redis.hget(session_key, "token")
                if token:
                    token_key = f"{self.token_prefix}{token}"
                    await redis.delete(token_key)
                await redis.delete(session_key)

            record_metric("auth.session.invalidate.success", 1)
        except Exception as e:
            record_metric("auth.session.invalidate.failure", 1)
            logger.error(f"Failed to invalidate session: {str(e)}")


class TokenManager:
    """Manages JWT token operations."""

    def __init__(self):
        self.algorithm = settings.ALGORITHM
        self.secret_key = settings.SECRET_KEY

    def create_token(self, subject: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {"exp": expire, "sub": str(subject)}
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            record_metric("auth.token.create.success", 1)
            return encoded_jwt
        except Exception as e:
            record_metric("auth.token.create.failure", 1)
            logger.error(f"Token creation failed: {str(e)}")
            raise AuthenticationError("Token creation failed")

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_data = TokenPayload(**payload)
            record_metric("auth.token.decode.success", 1)
            return token_data
        except JWTError as e:
            record_metric("auth.token.decode.failure", 1)
            logger.error(f"Token validation failed: {str(e)}")
            raise AuthenticationError("Could not validate credentials")


class RateLimiter:
    """Rate limiting implementation."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute

    async def check_limit(self, request: Request) -> None:
        """Check if request is within rate limits."""
        try:
            client_ip = request.client.host
            key = f"ratelimit:{client_ip}"

            async with redis_manager.connection() as redis:
                current = await redis.incr(key)
                if current == 1:
                    await redis.expire(key, self.window_size)

                if current > self.requests_per_minute:
                    record_metric("auth.ratelimit.exceeded", 1)
                    raise HTTPException(status_code=429, detail="Too many requests")

            record_metric("auth.ratelimit.check.success", 1)
        except Exception as e:
            record_metric("auth.ratelimit.check.failure", 1)
            logger.error(f"Rate limit check failed: {str(e)}")
            # Allow request on rate limit check failure
            return None


class AuthenticationFramework:
    """Comprehensive authentication framework."""

    def __init__(self):
        self.token_manager = TokenManager()
        self.session_store = SessionStore()
        self.rate_limiter = RateLimiter()

    async def authenticate_request(self, request: Request, db: AsyncSession, token: str) -> User:
        """Authenticate an incoming request."""
        # Check rate limit
        await self.rate_limiter.check_limit(request)

        # Validate token format
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")

        # Decode token
        token_data = self.token_manager.decode_token(token)

        # Validate session
        user_id = await self.session_store.validate_session(token)
        if not user_id:
            raise AuthenticationError("Invalid or expired session")

        # Get user
        user = await db.get(User, user_id)
        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("Inactive user")

        return user

    async def create_user_session(
        self, user: User, password: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """Create a new user session."""
        # Verify password
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect password")

        # Create token
        token = self.token_manager.create_token(str(user.id))

        # Create session
        await self.session_store.create_session(user.id, token)

        return {"access_token": token, "token_type": "bearer"}

    async def logout(self, user: User) -> None:
        """Logout user and invalidate session."""
        await self.session_store.invalidate_session(user.id)


# Global authentication framework instance
auth_framework = AuthenticationFramework()
