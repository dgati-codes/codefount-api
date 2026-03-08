"""
app/api/v1/endpoints/misc.py
==============================
Services, Schedules, Contact/Enquiry, Users (admin) endpoints.

Spring Boot equivalent
-----------------------
  @RestController classes: ServiceController, ScheduleController,
  EnquiryController, AdminUserController
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.misc import EnquiryCreate, EnquiryResponse, ScheduleResponse, ServiceResponse
from app.schemas.user import UserResponse
from app.services.misc_service import MiscService
from app.services.user_service import UserService


# ── Services (public) ─────────────────────────────────────────────────────────
services_router = APIRouter(prefix="/services", tags=["Services"])


@services_router.get("", response_model=List[ServiceResponse], summary="List all services (public)")
async def list_services(db: AsyncSession = Depends(get_db)) -> List[ServiceResponse]:
    """
    Spring Boot: @GetMapping("/api/v1/services")
    public List<ServiceResponse> list()  — no @PreAuthorize, open to all.
    """
    svc = MiscService(db)
    return [ServiceResponse.model_validate(i) for i in await svc.list_services()]


# ── Schedules (public) ────────────────────────────────────────────────────────
schedules_router = APIRouter(prefix="/schedules", tags=["Schedules"])


@schedules_router.get("", response_model=List[ScheduleResponse], summary="List training schedules (public)")
async def list_schedules(db: AsyncSession = Depends(get_db)) -> List[ScheduleResponse]:
    svc = MiscService(db)
    return [ScheduleResponse.model_validate(i) for i in await svc.list_schedules()]


# ── Enquiries / Contact form ───────────────────────────────────────────────────
enquiries_router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


@enquiries_router.post(
    "",
    response_model=EnquiryResponse,
    status_code=201,
    summary="Submit contact enquiry — guest (no login required)",
)
async def submit_enquiry_guest(
    body: EnquiryCreate,
    db:   AsyncSession = Depends(get_db),
) -> EnquiryResponse:
    """
    Any visitor (logged in or not) can submit a contact form.
    Spring Boot: .requestMatchers(POST, "/api/v1/enquiries").permitAll()
    """
    svc = MiscService(db)
    enquiry = await svc.create_enquiry(body, user=None)
    return EnquiryResponse.model_validate(enquiry)


@enquiries_router.post(
    "/me",
    response_model=EnquiryResponse,
    status_code=201,
    summary="Submit enquiry as authenticated user 🔒",
)
async def submit_enquiry_auth(
    body:         EnquiryCreate,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> EnquiryResponse:
    """
    Links the enquiry to the logged-in user account for follow-up tracking.
    Spring Boot: @PreAuthorize("isAuthenticated()")
    """
    svc = MiscService(db)
    enquiry = await svc.create_enquiry(body, user=current_user)
    return EnquiryResponse.model_validate(enquiry)


@enquiries_router.get("", response_model=List[EnquiryResponse], summary="List all enquiries [ADMIN]")
async def list_enquiries(
    db:     AsyncSession = Depends(get_db),
    _admin: User         = Depends(require_admin),
) -> List[EnquiryResponse]:
    """Spring Boot: @PreAuthorize("hasRole('ADMIN')")"""
    svc = MiscService(db)
    return [EnquiryResponse.model_validate(i) for i in await svc.list_enquiries()]


# ── Admin: User management ────────────────────────────────────────────────────
admin_users_router = APIRouter(prefix="/admin/users", tags=["Admin — Users"])


@admin_users_router.get("", response_model=List[UserResponse], summary="List all users [ADMIN]")
async def list_users(
    db:     AsyncSession = Depends(get_db),
    _admin: User         = Depends(require_admin),
) -> List[UserResponse]:
    """
    Spring Boot: @GetMapping @PreAuthorize("hasRole('ADMIN')")
    """
    result = await db.execute(select(User).order_by(User.id))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@admin_users_router.patch("/{user_id}/deactivate", status_code=204, summary="Deactivate a user [ADMIN]")
async def deactivate_user(
    user_id: int,
    db:      AsyncSession = Depends(get_db),
    _admin:  User         = Depends(require_admin),
) -> None:
    svc  = UserService(db)
    user = await svc.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await svc.deactivate(user)