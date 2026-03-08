"""
app/schemas/user.py
====================
Pydantic schemas for User — request bodies + response shapes.

Spring Boot equivalent
-----------------------
  DTOs (Data Transfer Objects):
    UserCreateRequest.java, UserUpdateRequest.java, UserResponse.java
  Pydantic's BaseModel  ≈  record / POJO + Jackson @JsonProperty annotations.
  field_validator        ≈  @NotBlank, @Email, @Size, custom @Constraint validators.
  model_config(from_attributes=True)  ≈  MapStruct mapper or ModelMapper.
"""

import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.user import UserRole


# ── Request schemas ───────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """POST /auth/register — Spring Boot: @RequestBody UserRegisterRequest"""
    full_name:    str
    email:        EmailStr
    password:     str
    phone:        Optional[str] = None
    gender:       Optional[str] = None
    country_code: Optional[str] = "+233"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Spring Boot equivalent: @Pattern(regexp="...", message="Weak password")"""
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
    """POST /auth/login — uses OAuth2PasswordRequestForm format"""
    email:    EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    """PATCH /users/me — partial update, all fields optional"""
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
    """
    Returned to the client. Never exposes hashed_password.
    Spring Boot: @JsonIgnore on hashed_password field in UserResponse DTO.
    """
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
    """JWT response shape — Spring Boot: JwtResponse DTO"""
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str