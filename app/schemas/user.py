"""
app/schemas/user.py
====================
Pydantic schemas for User — request bodies + response shapes.
"""

import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.user import UserRole


# ── Request schemas ───────────────────────────────────────────────────────────


class UserRegisterRequest(BaseModel):
    full_name:    str
    email:        EmailStr
    password:     str
    phone:        Optional[str] = None
    gender:       Optional[str] = None
    country_code: Optional[str] = "+233"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name is required")
        return v.strip()


class UserLoginRequest(BaseModel):
    email:    EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    full_name:    Optional[str]  = None
    phone:        Optional[str]  = None
    gender:       Optional[str]  = None
    country_code: Optional[str]  = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator("new_password")
    @classmethod
    def strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("New password must be at least 6 characters")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ≈ @Mapper(componentModel="spring")

    id:           int
    full_name:    str
    email:        str
    phone:        Optional[str]
    gender:       Optional[str]
    country_code: Optional[str]
    role:         UserRole
    is_active:    bool
    is_verified:  bool


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str
