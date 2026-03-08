"""
tests/conftest.py
==================
Pytest fixtures shared across all tests.

Spring Boot equivalent
-----------------------
  @SpringBootTest + @AutoConfigureMockMvc  →  TestClient
  @Transactional on test class             →  each test uses a rolled-back session
  @TestPropertySource(properties=...)      →  override DATABASE_URL to use test DB
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.main import app
# Explicit model imports — ensures all tables are in Base.metadata
from app.models.user import User, UserRole
from app.models.course import Course, CurriculumItem, Enrollment
from app.models.workshop import Workshop, WorkshopRegistration
from app.models.misc import Service, Schedule, Enquiry

# ── In-memory SQLite for unit tests (fast, no Postgres needed) ─────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create all tables once for the test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncSession:
    """
    Per-test DB session — rolls back after each test.
    Spring Boot: @Transactional on test method auto-rollback.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncClient:
    """
    Async HTTP test client.
    Spring Boot: MockMvc / TestRestTemplate autowired in @SpringBootTest.
    Overrides the get_db dependency to use the test session.
    """
    from app.core.dependencies import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def registered_user(client: AsyncClient) -> dict:
    """Creates a test user and returns the token response dict."""
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "test@codefount.com",
        "password": "Test@1234",
        "country_code": "+233",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture()
async def auth_headers(registered_user: dict) -> dict:
    """Bearer token headers for authenticated requests."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}