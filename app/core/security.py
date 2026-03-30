"""
app/core/security.py
=====================
JWT creation/verification + password hashing.

Spring Boot equivalent
-----------------------
  JwtUtil / JwtTokenProvider class  +  PasswordEncoder (BCryptPasswordEncoder).
  python-jose  ≈  io.jsonwebtoken (jjwt)
  passlib      ≈  org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# BCrypt context — equivalent to:
#   @Bean BCryptPasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Equivalent to passwordEncoder.encode(rawPassword)"""
    return _pwd_ctx.hash(plain)


# Alias used by misc.py / any code that imports get_password_hash
get_password_hash = hash_password


def verify_password(plain: str, hashed: str) -> bool:
    """Equivalent to passwordEncoder.matches(rawPassword, encodedPassword)"""
    return _pwd_ctx.verify(plain, hashed)


# ── JWT helpers ──────────────────────────────────────────────────────────────

def _create_token(subject: Any, expires_delta: timedelta, token_type: str) -> str:
    """
    Internal factory.
    Spring Boot equivalent: JwtUtil.generateToken(UserDetails userDetails)
    Claims map:  sub=user_id,  type=access|refresh,  exp=...,  iat=...
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int) -> str:
    """Short-lived token (30 min by default)."""
    return _create_token(
        user_id,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(user_id: int) -> str:
    """Long-lived token (7 days by default) for silent re-auth."""
    return _create_token(
        user_id,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str) -> dict:
    """
    Raises JWTError on invalid / expired tokens.
    Spring Boot equivalent: JwtUtil.validateToken(token) + extractClaims(token)
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
