"""
app/api/v1/endpoints/workshops.py
===================================
Public workshop listing.
Protected registration endpoints.

Spring Boot equivalent
-----------------------
  @RestController @RequestMapping("/api/v1/workshops") WorkshopController
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.workshop import (
    WorkshopCreate,
    WorkshopRegistrationResponse,
    WorkshopResponse,
    WorkshopUpdate,
)
from app.services.workshop_service import WorkshopRegistrationService, WorkshopService

router = APIRouter(prefix="/workshops", tags=["Workshops"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/workshops    PUBLIC
# ?free_only=true|false   (omit for all)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("", response_model=dict, summary="List workshops (public)")
async def list_workshops(
    free_only: Optional[bool] = Query(None, description="true=free only, false=paid only"),
    page:      int            = Query(1, ge=1),
    size:      int            = Query(20, ge=1, le=50),
    db:        AsyncSession   = Depends(get_db),
) -> dict:
    """
    Spring Boot:
        @GetMapping
        public Page<WorkshopResponse> list(@RequestParam Optional<Boolean> freeOnly, Pageable pg)
    """
    svc  = WorkshopService(db)
    skip = (page - 1) * size
    workshops, total = await svc.list_workshops(free_only=free_only, skip=skip, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [WorkshopResponse.model_validate(w) for w in workshops],
    }


# GET /api/v1/workshops/{id}   PUBLIC
@router.get("/{workshop_id}", response_model=WorkshopResponse, summary="Workshop detail (public)")
async def get_workshop(
    workshop_id: int,
    db: AsyncSession = Depends(get_db),
) -> WorkshopResponse:
    svc      = WorkshopService(db)
    workshop = await svc.get_by_id(workshop_id)
    if workshop is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return WorkshopResponse.model_validate(workshop)


# POST /api/v1/workshops   🔒🛡️ ADMIN
@router.post("", response_model=WorkshopResponse, status_code=201, summary="Create workshop [ADMIN]")
async def create_workshop(
    body:   WorkshopCreate,
    db:     AsyncSession = Depends(get_db),
    _admin: User         = Depends(require_admin),
) -> WorkshopResponse:
    svc = WorkshopService(db)
    ws  = await svc.create(body)
    return WorkshopResponse.model_validate(ws)


# PATCH /api/v1/workshops/{id}   🔒🛡️ ADMIN
@router.patch("/{workshop_id}", response_model=WorkshopResponse, summary="Update workshop [ADMIN]")
async def update_workshop(
    workshop_id: int,
    body:        WorkshopUpdate,
    db:          AsyncSession = Depends(get_db),
    _admin:      User         = Depends(require_admin),
) -> WorkshopResponse:
    svc = WorkshopService(db)
    ws  = await svc.get_by_id(workshop_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    updated = await svc.update(ws, body)
    return WorkshopResponse.model_validate(updated)


# DELETE /api/v1/workshops/{id}   🔒🛡️ ADMIN
@router.delete("/{workshop_id}", status_code=204, summary="Delete workshop [ADMIN]")
async def delete_workshop(
    workshop_id: int,
    db:          AsyncSession = Depends(get_db),
    _admin:      User         = Depends(require_admin),
) -> None:
    svc = WorkshopService(db)
    ws  = await svc.get_by_id(workshop_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    await svc.delete(ws)


# ═════════════════════════════════════════════════════════════════════════════
# REGISTRATIONS  /api/v1/workshops/registrations
# ═════════════════════════════════════════════════════════════════════════════
reg_router = APIRouter(prefix="/workshop-registrations", tags=["Workshop Registrations"])


# GET /api/v1/workshop-registrations/my   🔒 PROTECTED
@reg_router.get("/my", response_model=List[WorkshopRegistrationResponse], summary="My workshop registrations")
async def my_registrations(
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> List[WorkshopRegistrationResponse]:
    svc  = WorkshopRegistrationService(db)
    regs = await svc.get_user_registrations(current_user.id)
    return [WorkshopRegistrationResponse.model_validate(r) for r in regs]


# POST /api/v1/workshop-registrations/{workshop_id}   🔒 PROTECTED
@reg_router.post(
    "/{workshop_id}",
    response_model=WorkshopRegistrationResponse,
    status_code=201,
    summary="Register for a workshop",
)
async def register_workshop(
    workshop_id:  int,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> WorkshopRegistrationResponse:
    """
    Spring Boot: @PostMapping("/{workshopId}")
    @Transactional — checks seats, saves registration, increments filled count atomically.
    """
    svc = WorkshopRegistrationService(db)
    try:
        reg = await svc.register(current_user.id, workshop_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # Reload with workshop relation
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.workshop import WorkshopRegistration
    result = await db.execute(
        select(WorkshopRegistration)
        .options(selectinload(WorkshopRegistration.workshop))
        .where(WorkshopRegistration.id == reg.id)
    )
    return WorkshopRegistrationResponse.model_validate(result.scalar_one())


# DELETE /api/v1/workshop-registrations/{workshop_id}   🔒 PROTECTED
@reg_router.delete("/{workshop_id}", status_code=204, summary="Cancel workshop registration")
async def cancel_registration(
    workshop_id:  int,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> None:
    svc = WorkshopRegistrationService(db)
    await svc.cancel(current_user.id, workshop_id)