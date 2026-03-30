"""
app/api/v1/router.py
=====================
Master API router — registers all sub-routers.

  include_router(auth_router)           ≈  AuthController mapped to /api/v1/auth/*
  include_router(courses_router)        ≈  CourseController mapped to /api/v1/courses/*
  include_router(testimonials_router)   ≈  TestimonialController
  include_router(notifications_router)  ≈  NotificationController
  include_router(resources_router)      ≈  TutorResourceController
  include_router(payment_proofs_router) ≈  PaymentProofController
  include_router(reports_router)        ≈  AdminReportController
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
from app.api.v1.endpoints.testimonials import router as testimonials_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.resources import router as resources_router
from app.api.v1.endpoints.payment_proofs import router as payment_proofs_router
from app.api.v1.endpoints.reports import router as reports_router


api_router = APIRouter()

# ── Existing routes (unchanged) ───────────────────────────────────────────────
api_router.include_router(auth_router)            # /auth/*
api_router.include_router(courses_router)         # /courses/*
api_router.include_router(enroll_router)          # /enrollments/*
api_router.include_router(workshops_router)       # /workshops/*
api_router.include_router(ws_reg_router)          # /workshop-registrations/*
api_router.include_router(services_router)        # /services
api_router.include_router(schedules_router)       # /schedules
api_router.include_router(enquiries_router)       # /enquiries/*
api_router.include_router(admin_users_router)     # /admin/users/*
api_router.include_router(testimonials_router)  # /testimonials/*
api_router.include_router(notifications_router)  # /notifications/*
api_router.include_router(resources_router)  # /courses/{id}/resources, /resources/*
api_router.include_router(payment_proofs_router)  # /payment-proofs/*
api_router.include_router(reports_router)  # /admin/reports/*
