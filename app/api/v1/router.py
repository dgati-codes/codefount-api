"""
app/api/v1/router.py
=====================
Master API router — registers all sub-routers.

Spring Boot equivalent
-----------------------
  This file is equivalent to the central SecurityConfig / WebMvcConfig
  that maps URL prefixes to controller packages, PLUS the individual
  @RequestMapping annotations on each @RestController.

  include_router(auth_router)         ≈  AuthController mapped to /api/v1/auth/*
  include_router(courses_router)      ≈  CourseController mapped to /api/v1/courses/*
  ...etc
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.courses import enroll_router, router as courses_router
from app.api.v1.endpoints.misc import (
    admin_users_router,
    enquiries_router,
    schedules_router,
    services_router,
)
from app.api.v1.endpoints.workshops import reg_router as ws_reg_router
from app.api.v1.endpoints.workshops import router as workshops_router

api_router = APIRouter()

# Public + Auth
api_router.include_router(auth_router)            # /auth/*
api_router.include_router(courses_router)         # /courses/*
api_router.include_router(enroll_router)          # /enrollments/*
api_router.include_router(workshops_router)       # /workshops/*
api_router.include_router(ws_reg_router)          # /workshop-registrations/*
api_router.include_router(services_router)        # /services
api_router.include_router(schedules_router)       # /schedules
api_router.include_router(enquiries_router)       # /enquiries/*
api_router.include_router(admin_users_router)     # /admin/users/*