"""
app/api/v1/endpoints/misc.py
==============================
Misc domain routers: schedules, services, enquiries, admin-users.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.core.security import get_password_hash  # alias for hash_password
from app.models.user import User, UserRole
from app.schemas.misc import (
    EnquiryCreate,
    EnquiryResponse,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
)
from app.schemas.user import UserResponse
from app.services.user_service import UserService

# ── Schedules ─────────────────────────────────────────────────────────────────
schedules_router = APIRouter(prefix="/schedules", tags=["Schedules"])


@schedules_router.get("", response_model=List[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db)):
    from app.models.misc import Schedule

    result = await db.execute(select(Schedule).order_by(Schedule.id))
    return [ScheduleResponse.model_validate(s) for s in result.scalars().all()]


@schedules_router.post(
    "",
    response_model=ScheduleResponse,
    status_code=201,
    summary="Create a schedule entry [ADMIN]",
)
async def create_schedule(
    body: ScheduleCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Schedule

    item = Schedule(**body.model_dump())
    db.add(item)
    await db.flush()
    return ScheduleResponse.model_validate(item)


@schedules_router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Update a schedule entry [ADMIN]",
)
async def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Schedule

    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Schedule not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    return ScheduleResponse.model_validate(item)


@schedules_router.delete(
    "/{schedule_id}", status_code=204, summary="Delete a schedule entry [ADMIN]"
)
async def delete_schedule(
    schedule_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Schedule

    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Schedule not found")
    await db.delete(item)


# ── Services ──────────────────────────────────────────────────────────────────
services_router = APIRouter(prefix="/services", tags=["Services"])


@services_router.get("", response_model=List[ServiceResponse])
async def list_services(db: AsyncSession = Depends(get_db)):
    from app.models.misc import Service

    result = await db.execute(select(Service).order_by(Service.order))
    return [ServiceResponse.model_validate(s) for s in result.scalars().all()]


@services_router.post(
    "",
    response_model=ServiceResponse,
    status_code=201,
    summary="Create a service [ADMIN]",
)
async def create_service(
    body: ServiceCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Service

    item = Service(**body.model_dump())
    db.add(item)
    await db.flush()
    return ServiceResponse.model_validate(item)


@services_router.patch(
    "/{service_id}", response_model=ServiceResponse, summary="Update a service [ADMIN]"
)
async def update_service(
    service_id: int,
    body: ServiceUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Service

    result = await db.execute(select(Service).where(Service.id == service_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Service not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    return ServiceResponse.model_validate(item)


@services_router.delete(
    "/{service_id}", status_code=204, summary="Delete a service [ADMIN]"
)
async def delete_service(
    service_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Service

    result = await db.execute(select(Service).where(Service.id == service_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Service not found")
    await db.delete(item)


# ── Enquiries ─────────────────────────────────────────────────────────────────
enquiries_router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


@enquiries_router.get(
    "", response_model=List[EnquiryResponse], summary="List all enquiries [ADMIN]"
)
async def list_enquiries(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Enquiry

    result = await db.execute(select(Enquiry).order_by(Enquiry.created_at.desc()))
    return [EnquiryResponse.model_validate(e) for e in result.scalars().all()]


@enquiries_router.post(
    "",
    response_model=EnquiryResponse,
    status_code=201,
    summary="Submit a contact enquiry (guest)",
)
async def submit_enquiry(
    body: EnquiryCreate,
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Enquiry

    item = Enquiry(**body.model_dump())
    db.add(item)
    await db.flush()
    return EnquiryResponse.model_validate(item)


@enquiries_router.post(
    "/me",
    response_model=EnquiryResponse,
    status_code=201,
    summary="Submit a contact enquiry (authenticated user)",
)
async def submit_enquiry_auth(
    body: EnquiryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.misc import Enquiry

    item = Enquiry(**body.model_dump(), user_id=current_user.id)
    db.add(item)
    await db.flush()
    return EnquiryResponse.model_validate(item)


# ── Admin Users ───────────────────────────────────────────────────────────────
admin_users_router = APIRouter(prefix="/admin/users", tags=["Admin — Users"])


class AdminUserCreateBody(BaseModel):
    """Request body for admin-created user accounts (any role)."""

    full_name: str
    email: str
    password: str
    role: str = "student"  # student | trainer | admin
    phone: Optional[str] = None
    gender: Optional[str] = None
    country_code: str = "+233"
    is_active: bool = True


class AdminUserUpdateBody(BaseModel):
    """Partial profile update by admin."""

    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    country_code: Optional[str] = None


@admin_users_router.get(
    "",
    response_model=List[UserResponse],
    summary="List all users [ADMIN]",
)
async def list_users(
    role: Optional[str] = Query(None, description="Filter: student|trainer|admin"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> List[UserResponse]:
    q = select(User).order_by(User.id)
    if role and role in ("student", "trainer", "admin"):
        q = q.where(User.role == role)
    if search:
        from sqlalchemy import or_

        like = f"%{search}%"
        q = q.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@admin_users_router.post(
    "",
    status_code=201,
    summary="Create a user account of any role [ADMIN]",
)
async def admin_create_user(
    body: AdminUserCreateBody,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """
    Admin creates Student, Tutor, or Admin accounts directly.
    Created accounts are pre-verified — no email confirmation required.
    """
    if body.role not in ("student", "trainer", "admin"):
        raise HTTPException(400, "Invalid role. Must be student, trainer, or admin.")

    email = body.email.strip().lower()
    existing = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "A user with this email already exists.")

    if len(body.password) < 6:
        raise HTTPException(422, "Password must be at least 6 characters.")

    new_user = User(
        full_name=body.full_name.strip(),
        email=email,
        hashed_password=get_password_hash(body.password),
        role=body.role,
        phone=body.phone,
        gender=body.gender,
        country_code=body.country_code,
        is_active=body.is_active,
        is_verified=True,  # admin-created accounts skip email verification
    )
    db.add(new_user)
    await db.flush()
    return UserResponse.model_validate(new_user).model_dump()


@admin_users_router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user's profile [ADMIN]",
)
async def admin_update_user(
    user_id: int,
    body: AdminUserUpdateBody,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "User not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    await db.flush()
    return UserResponse.model_validate(user)


@admin_users_router.patch(
    "/{user_id}/role",
    status_code=200,
    summary="Change user role [ADMIN]",
)
async def change_user_role(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "User not found")
    new_role = body.get("role") if isinstance(body, dict) else None
    if new_role not in ("student", "trainer", "admin"):
        raise HTTPException(400, "Invalid role. Must be student, trainer, or admin.")
    user.role = new_role
    await db.flush()
    return {"id": user.id, "role": user.role}


@admin_users_router.patch(
    "/{user_id}/deactivate",
    status_code=204,
    summary="Deactivate a user [ADMIN]",
)
async def deactivate_user(
    user_id: int,
    db:      AsyncSession = Depends(get_db),
    _admin:  User         = Depends(require_admin),
) -> None:
    svc  = UserService(db)
    user = await svc.get_by_id(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    await svc.deactivate(user)


@admin_users_router.patch(
    "/{user_id}/activate",
    status_code=204,
    summary="Re-activate a user [ADMIN]",
)
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "User not found")
    user.is_active = True
    await db.flush()


@admin_users_router.delete(
    "/{user_id}",
    status_code=204,
    summary="Delete a user account [ADMIN]",
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "User not found")
    await db.delete(user)
