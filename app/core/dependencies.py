"""
app/core/dependencies.py
=========================
FastAPI dependency-injection helpers.

Spring Boot equivalent
-----------------------
  FastAPI's Depends()  ≈  Spring's @Autowired / constructor injection.
  get_db()             ≈  @PersistenceContext EntityManager  or  JPA Repository autowired per-request.
  get_current_user()   ≈  Spring Security's SecurityContextHolder / @AuthenticationPrincipal.
  require_admin()      ≈  @PreAuthorize("hasRole('ADMIN')")
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.user_service import UserService

# Tells FastAPI where clients send the Bearer token.
# Spring Boot equivalent: the URL configured in HttpSecurity.oauth2ResourceServer(...)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Database session ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async DB session per request, always closes it.
    Spring Boot equivalent: @Transactional on a service method, or
      EntityManager injected with @PersistenceContext (request scope).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Authenticated user ────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates the Bearer JWT and returns the User model.
    Spring Boot equivalent:
      JwtAuthenticationFilter.doFilterInternal()  +
      @AuthenticationPrincipal UserDetails currentUser
    Raises 401 on missing / invalid token, 404 if user deleted mid-session.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    svc = UserService(db)
    user = await svc.get_by_id(int(user_id))
    if user is None:
        raise credentials_exc
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Convenience alias — same as get_current_user but named for readability."""
    return current_user


# ── Role-based guards ─────────────────────────────────────────────────────────

async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Spring Boot equivalent: @PreAuthorize("hasRole('ADMIN')")
    Raises 403 if the user is not an admin.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user