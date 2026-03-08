"""
app/core/config.py
==================
Centralised settings using Pydantic-Settings.

Spring Boot equivalent
-----------------------
  application.properties / application.yml  +  @ConfigurationProperties classes.
  Pydantic's BaseSettings reads from environment variables and .env files
  exactly like @Value / @ConfigurationProperties, with full type validation.
"""

from functools import lru_cache
from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "CodeFount API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Database ─────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/codefount_db"
    DATABASE_ECHO: bool = False

    # ── Security ─────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # ── Superuser seed ────────────────────────
    FIRST_SUPERUSER_EMAIL: str = "admin@codefount.com"
    FIRST_SUPERUSER_PASSWORD: str = "Admin@1234"

    # ── API prefix ────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()          # singleton — same as @Bean with @Scope("singleton")
def get_settings() -> Settings:
    return Settings()


settings = get_settings()