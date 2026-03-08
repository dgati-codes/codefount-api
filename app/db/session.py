"""
app/db/session.py
==================
Async SQLAlchemy engine and session factory.

Spring Boot equivalent
-----------------------
  DataSource bean  +  HikariCP connection pool  +  EntityManagerFactory.
  SQLAlchemy's create_async_engine  ≈  HikariDataSource configuration.
  AsyncSession                      ≈  EntityManager (per-request scope).
  AsyncSessionLocal (sessionmaker)  ≈  EntityManagerFactory.createEntityManager()
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# pool_size / max_overflow  ≈  HikariCP maximumPoolSize
# NullPool used in tests to avoid cross-test contamination
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,          # validates connection before use — like HikariCP testQuery
    pool_recycle=3600,           # recycle connections after 1h
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,      # keeps attributes accessible after commit
    autoflush=False,
)