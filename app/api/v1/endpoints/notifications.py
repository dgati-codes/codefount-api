"""
app/api/v1/endpoints/notifications.py
=======================================
Admin/trainer broadcast + student inbox endpoints.

Spring Boot equivalent
-----------------------
  @RestController @RequestMapping("/api/v1/notifications") NotificationController

ADMIN/TRAINER  🔒🛡️  — POST broadcast, GET sent list
STUDENT        🔒     — GET inbox, PATCH mark-read, PATCH mark-all-read, GET unread count
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    UserNotificationResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/notifications/broadcast     🔒 ADMIN or TRAINER
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/broadcast",
    response_model=NotificationResponse,
    status_code=201,
    summary="Broadcast a notification to students/tutors [ADMIN or TRAINER]",
)
async def broadcast(
    body:         NotificationCreate,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """
    Admin can broadcast to any target.
    Trainer can broadcast to students of their own courses.

    Spring Boot:
      @PostMapping("/broadcast")
      @PreAuthorize("hasAnyRole('ADMIN','TRAINER')")
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.TRAINER):
        raise HTTPException(status_code=403, detail="Admin or trainer privileges required")

    svc   = NotificationService(db)
    notif = await svc.broadcast(body, sender=current_user)
    return NotificationResponse.model_validate(notif)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/notifications/sent          🔒🛡️ ADMIN
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/sent",
    response_model=dict,
    summary="List all sent notifications [ADMIN]",
)
async def list_sent(
    page:   int          = Query(1, ge=1),
    size:   int          = Query(20, ge=1, le=50),
    db:     AsyncSession = Depends(get_db),
    _admin: User         = Depends(require_admin),
) -> dict:
    """Spring Boot: @GetMapping("/sent") @PreAuthorize("hasRole('ADMIN')")"""
    svc  = NotificationService(db)
    skip = (page - 1) * size
    items, total = await svc.list_sent(skip=skip, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [NotificationResponse.model_validate(n) for n in items],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/notifications/me           🔒 STUDENT — inbox
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=dict,
    summary="My notification inbox 🔒",
)
async def my_inbox(
    unread_only:  bool         = Query(False),
    page:         int          = Query(1, ge=1),
    size:         int          = Query(20, ge=1, le=50),
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the authenticated user's notification deliveries.
    Spring Boot:
      @GetMapping("/me")
      @PreAuthorize("isAuthenticated()")
      Page<UserNotificationResponse> inbox(@AuthenticationPrincipal User user, ...)
    """
    svc  = NotificationService(db)
    skip = (page - 1) * size
    deliveries, total = await svc.get_user_inbox(
        current_user.id, unread_only=unread_only, skip=skip, limit=size
    )
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [UserNotificationResponse.from_orm_delivery(d) for d in deliveries],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/notifications/me/unread-count   🔒 STUDENT — navbar badge
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/me/unread-count",
    response_model=dict,
    summary="My unread notification count (for navbar badge) 🔒",
)
async def unread_count(
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> dict:
    svc   = NotificationService(db)
    count = await svc.unread_count(current_user.id)
    return {"unread": count}


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/notifications/me/{delivery_id}/read   🔒 STUDENT
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/me/{delivery_id}/read",
    status_code=204,
    summary="Mark a notification as read 🔒",
)
async def mark_read(
    delivery_id:  int,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> None:
    """
    Spring Boot: @PatchMapping("/me/{id}/read") @PreAuthorize("isAuthenticated()")
    404 if the delivery doesn't belong to this user.
    """
    svc      = NotificationService(db)
    delivery = await svc.mark_read(delivery_id, current_user.id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Notification not found")


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/notifications/me/read-all   🔒 STUDENT
# ─────────────────────────────────────────────────────────────────────────────
@router.patch(
    "/me/read-all",
    response_model=dict,
    summary="Mark all notifications as read 🔒",
)
async def mark_all_read(
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> dict:
    svc   = NotificationService(db)
    count = await svc.mark_all_read(current_user.id)
    return {"marked_read": count}