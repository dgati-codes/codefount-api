"""
app/api/v1/endpoints/auth.py
=============================
Authentication endpoints: register, login, refresh, me.

Spring Boot equivalent
-----------------------
  @RestController @RequestMapping("/api/v1/auth") AuthController
  Each function below  ≈  @PostMapping / @GetMapping method in that controller.

  FastAPI's APIRouter   ≈  @RestController class
  Depends(get_db)       ≈  @Autowired UserService (but per-request scoped)
  HTTPException(401)    ≈  throw new UnauthorizedException(...)
  response_model=       ≈  @ResponseBody + Jackson serialisation (hides fields not in schema)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user_service import UserService
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/register
# Spring Boot: @PostMapping("/register") ResponseEntity<UserResponse> register(
#                @Valid @RequestBody UserRegisterRequest body)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
async def register(
    body: UserRegisterRequest,          # ≈ @Valid @RequestBody
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Creates a new STUDENT account and immediately returns JWT tokens
    so the user is logged in right after registration.

    Spring Boot pattern:
        User user = userService.create(body);
        String token = jwtUtil.generateToken(user);
        return ResponseEntity.status(201).body(new TokenResponse(token, user));
    """
    svc = UserService(db)
    try:
        user = await svc.create(body)
    except ValueError as exc:
        # Duplicate email → 409 Conflict (Spring: throw new ConflictException)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/login
# Spring Boot: @PostMapping("/login") using DaoAuthenticationProvider
#   + AuthenticationManager.authenticate(new UsernamePasswordAuthenticationToken(...))
#
# NOTE: OAuth2PasswordRequestForm sends email as "username" (OAuth2 spec).
#   The React frontend must send  { username: email, password }  as form-data,
#   OR we accept JSON via UserLoginRequest (see /login-json below).
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login — returns access + refresh tokens",
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),  # ≈ @RequestParam("username") + @RequestParam("password")
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc  = UserService(db)
    user = await svc.authenticate(form.username, form.password)  # username field holds the email
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


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/login-json   (convenience for React frontend — accepts JSON)
# ─────────────────────────────────────────────────────────────────────────────
from app.schemas.user import UserLoginRequest  # noqa: E402

@router.post("/login-json", response_model=TokenResponse, summary="Login with JSON body")
async def login_json(
    body: UserLoginRequest,
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc  = UserService(db)
    user = await svc.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/refresh
# Spring Boot: @PostMapping("/refresh") — validate refresh token, issue new access token
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse, summary="Exchange refresh token for new tokens")
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
    except (JWTError, KeyError):
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


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/auth/me   🔒 PROTECTED
# Spring Boot: @GetMapping("/me") UserResponse me(@AuthenticationPrincipal User user)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
async def get_me(
    current_user: User = Depends(get_current_active_user),  # ≈ @AuthenticationPrincipal
) -> UserResponse:
    return UserResponse.model_validate(current_user)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/auth/me   🔒 PROTECTED
# Spring Boot: @PatchMapping("/me") ResponseEntity<UserResponse> updateMe(...)
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/me", response_model=UserResponse, summary="Update current user profile")
async def update_me(
    body:         UserUpdateRequest,
    current_user: User           = Depends(get_current_active_user),
    db:           AsyncSession   = Depends(get_db),
) -> UserResponse:
    svc  = UserService(db)
    user = await svc.update(current_user, body)
    return UserResponse.model_validate(user)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/change-password   🔒 PROTECTED
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Change password")
async def change_password(
    body:         ChangePasswordRequest,
    current_user: User           = Depends(get_current_active_user),
    db:           AsyncSession   = Depends(get_db),
) -> None:
    svc = UserService(db)
    try:
        await svc.change_password(current_user, body.current_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))