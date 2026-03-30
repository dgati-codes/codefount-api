"""
app/api/v1/endpoints/auth.py
==============================
Authentication endpoints — register, login (form + JSON), refresh, me,
update-me, change-password, avatar upload.

Role-based login: TokenResponse always includes the full user object so the
frontend can read user.role and redirect accordingly:
    admin   → /admin
    trainer → /tutor
    student → /profile  (or the original deep-link destination)
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
)
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Register ──────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
async def register(
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Creates a STUDENT account and returns JWT tokens so the user is
    immediately authenticated.  Frontend should redirect to /profile.
    """
    svc = UserService(db)
    try:
        user = await svc.create(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Login (OAuth2 form — for Swagger UI) ─────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login (form-data) — returns access + refresh tokens",
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc  = UserService(db)
    user = await svc.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Login JSON (React frontend primary login endpoint) ────────────────────────
@router.post(
    "/login-json",
    response_model=TokenResponse,
    summary="Login with JSON body — user.role drives frontend redirect",
)
async def login_json(
    body: UserLoginRequest,
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Returns TokenResponse with full user object including role.
    Frontend AuthContext reads user.role to decide the redirect destination:
        "admin"   → navigate('/admin')
        "trainer" → navigate('/tutor')
        "student" → navigate('/profile') or original intended URL
    """
    svc  = UserService(db)
    user = await svc.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Refresh token ─────────────────────────────────────────────────────────────
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange refresh token for a new token pair",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exc
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exc

    svc  = UserService(db)
    user = await svc.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exc

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Get current user ──────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user 🔒",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


# ── Update profile ────────────────────────────────────────────────────────────
@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile 🔒",
)
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    svc  = UserService(db)
    user = await svc.update(current_user, body)
    return UserResponse.model_validate(user)


# ── Change password ───────────────────────────────────────────────────────────
@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password 🔒",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = UserService(db)
    try:
        await svc.change_password(current_user, body.current_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Avatar upload ─────────────────────────────────────────────────────────────
AVATAR_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads")) / "avatars"
ALLOWED_IMG = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    summary="Upload profile photo 🔒",
)
async def upload_avatar(
    file: UploadFile = File(..., description="JPEG/PNG/WebP/GIF ≤ 2 MB"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    ct = file.content_type or ""
    if ct not in ALLOWED_IMG:
        raise HTTPException(422, f"Unsupported image type '{ct}'")
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(422, "Avatar must be ≤ 2 MB")
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "avatar").suffix
    filename = f"{uuid.uuid4().hex}{ext}"
    (AVATAR_DIR / filename).write_bytes(contents)
    current_user.avatar_url = f"/static/avatars/{filename}"
    db.add(current_user)
    await db.flush()
    return UserResponse.model_validate(current_user)
