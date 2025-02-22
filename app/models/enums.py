"""Enum models."""
from enum import Enum


class UserRole(str, Enum):
    """User role enum."""

    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"
