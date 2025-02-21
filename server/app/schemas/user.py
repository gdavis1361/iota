from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, constr, Field, ConfigDict, validator
import re

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = True

# Password validation regex patterns
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$")

# Properties to receive via API on creation
class UserCreate(UserBase):
    """User creation schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number")
    role: str = "USER"
    confirm_password: str = Field(..., min_length=8)
    is_superuser: bool = False
    is_verified: bool = False

    @validator("password")
    def validate_password_strength(cls, v):
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number"
            )
        return v

    @validator("confirm_password")
    def validate_passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("role")
    def validate_role(cls, v):
        if v not in ["ADMIN", "USER"]:
            raise ValueError("Role must be either 'ADMIN' or 'USER'")
        return v

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None
    phone_number: Optional[str] = None

# Properties to return via API
class UserResponse(UserBase):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

# Properties for token response
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# Properties for token data
class TokenData(BaseModel):
    user_id: Optional[int] = None

# Properties for password change
class PasswordChange(BaseModel):
    current_password: str
    new_password: constr(min_length=8)
    confirm_password: str

    @validator("new_password")
    def validate_password_strength(cls, v):
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number"
            )
        return v

    @validator("confirm_password")
    def validate_passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v

# Properties for password reset request
class PasswordResetRequest(BaseModel):
    email: EmailStr

# Properties for password reset
class PasswordReset(BaseModel):
    token: str
    new_password: constr(min_length=8)
    confirm_password: str

    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")

# Properties for email verification
class EmailVerification(BaseModel):
    token: str

# Properties for toggling user active status
class UserToggleActive(BaseModel):
    is_active: bool = Field(..., description="Whether the user should be active or not")
