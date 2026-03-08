"""
app/main.py
===========
Application entry point — creates the FastAPI app, wires middleware,
exception handlers, startup events and the API router.

Spring Boot equivalent
-----------------------
  @SpringBootApplication main class  +  WebMvcConfigurer  +  SecurityConfig.
  app = FastAPI(...)                 ≈  SpringApplication.run(...)
  app.add_middleware(CORSMiddleware) ≈  corsConfigurationSource() bean in SecurityConfig
  @app.on_event("startup")          ≈  ApplicationRunner / @PostConstruct / CommandLineRunner
  app.include_router(api_router)    ≈  @ComponentScan picking up all @RestController beans
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.utils.exceptions import register_exception_handlers

# ── Logging setup ─────────────────────────────────────────────────────────────
# Spring Boot: application.properties  logging.level.root=INFO
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("codefount")


# ── Lifespan (startup + shutdown) ─────────────────────────────────────────────
# Spring Boot equivalent: ApplicationRunner.run() + @PreDestroy / SmartLifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("🚀  CodeFount API starting  [%s]", settings.APP_ENV)

    # Ensure all tables exist (dev convenience — use Alembic in production)
    if not settings.is_production:
        from app.db.base import Base
        # Import all models explicitly — same reason as seed.py (FK resolution order)
        from app.models.user import User, UserRole
        from app.models.course import Course, CurriculumItem, Enrollment
        from app.models.workshop import Workshop, WorkshopRegistration
        from app.models.misc import Service, Schedule, Enquiry
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅  Database tables verified")

    # Seed superuser
    from app.db.session import AsyncSessionLocal
    from app.services.user_service import UserService
    async with AsyncSessionLocal() as db:
        try:
            svc = UserService(db)
            await svc.ensure_superuser(
                settings.FIRST_SUPERUSER_EMAIL,
                settings.FIRST_SUPERUSER_PASSWORD,
            )
            await db.commit()
            logger.info("✅  Superuser ready  [%s]", settings.FIRST_SUPERUSER_EMAIL)
        except Exception as exc:
            logger.warning("Superuser seed skipped: %s", exc)

    yield  # ← application runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    await engine.dispose()
    logger.info("👋  CodeFount API shutdown complete")


# ── App factory ───────────────────────────────────────────────────────────────
# Spring Boot: @SpringBootApplication — this is the equivalent bootstrap.
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## CodeFount IT Training Platform — REST API

**Authentication**
- `POST /api/v1/auth/register`  — create account → returns JWT
- `POST /api/v1/auth/login-json` — login → returns JWT
- `POST /api/v1/auth/refresh`   — swap refresh token for new access token

**Public routes** — no token needed  
Courses, Workshops, Services, Schedules, Enquiries (guest)

**Protected routes** 🔒 — `Authorization: Bearer <token>`  
My profile, Enrollments, Workshop registrations, Submit enquiry as user

**Admin routes** 🔒🛡️ — requires `role=admin`  
Create/edit courses & workshops, list enquiries, manage users
        """,
        docs_url="/docs",           # Swagger UI  — disable in prod: docs_url=None
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Spring Boot: corsConfigurationSource() in SecurityConfig
    # .allowedOrigins(...)  .allowedMethods(...)  .allowedHeaders(...)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── GZip compression ─────────────────────────────────────────────────────
    # Spring Boot: server.compression.enabled=true
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Request timing middleware ─────────────────────────────────────────────
    # Spring Boot: OncePerRequestFilter / HandlerInterceptor for timing
    @app.middleware("http")
    async def add_process_time(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
        if settings.DEBUG:
            logger.debug("%s %s → %s  (%.1fms)",
                         request.method, request.url.path,
                         response.status_code, elapsed)
        return response

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routes ───────────────────────────────────────────────────────────────
    # Spring Boot: @ComponentScan auto-detects @RestController beans.
    # Here we explicitly include the master router.
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health check ──────────────────────────────────────────────────────────
    # Spring Boot: spring-boot-starter-actuator  GET /actuator/health
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": settings.APP_VERSION})

    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse({
            "name":    settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs":    "/docs",
        })

    return app


app = create_app()