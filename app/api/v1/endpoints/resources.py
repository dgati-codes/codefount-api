"""
app/api/v1/endpoints/resources.py
====================================
Tutor-shared learning resources per course.

Access rules:
  ENROLLED STUDENT 🔒   — GET /courses/{id}/resources, GET /resources/me
  TRAINER          🔒🛡  — POST /resources, PATCH /resources/{id}, DELETE /resources/{id}
  ADMIN            🔒🛡  — all of the above

Spring Boot equivalent
-----------------------
  @RestController @RequestMapping("/api/v1/resources") TutorResourceController
  @PreAuthorize checked per method
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db
from app.models.user import User, UserRole
from app.schemas.resource import (
    TutorResourceCreate,
    TutorResourceResponse,
    TutorResourceUpdate,
)
from app.services.resource_service import TutorResourceService

router = APIRouter(tags=["Tutor Resources"])


# ── GET /courses/{id}/resources  🔒 enrolled student OR trainer/admin ────────
@router.get(
    "/courses/{course_id}/resources",
    response_model=dict,
    summary="List resources for a course 🔒",
)
async def list_course_resources(
    course_id:    int,
    page:         int          = Query(1, ge=1),
    size:         int          = Query(50, ge=1, le=100),
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> dict:
    """
    Students must be actively enrolled.
    Trainers and admins always have access.

    Spring Boot:
      @GetMapping("/courses/{courseId}/resources")
      @PreAuthorize("isAuthenticated()")
      — enrollment check enforced in service layer
    """
    svc = TutorResourceService(db)
    if current_user.role == UserRole.STUDENT:
        if not await svc.is_enrolled(current_user.id, course_id):
            raise HTTPException(
                403,
                "You must be enrolled in this course to view its resources.",
            )
    skip         = (page - 1) * size
    items, total = await svc.list_for_course(course_id, skip=skip, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [TutorResourceResponse.from_orm(r) for r in items],
    }


# ── GET /resources/me  🔒 student — all resources across enrolled courses ─────
@router.get(
    "/resources/me",
    response_model=List[TutorResourceResponse],
    summary="All my resources across enrolled courses 🔒",
)
async def my_resources(
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> List[TutorResourceResponse]:
    """
    Drives the student's Resources tab on the Profile page.
    Spring Boot:
      @GetMapping("/me") @PreAuthorize("isAuthenticated()")
    """
    svc   = TutorResourceService(db)
    items = await svc.list_for_enrolled_user(current_user.id)
    return [TutorResourceResponse.from_orm(r) for r in items]


# ── POST /resources  🔒🛡 trainer or admin ────────────────────────────────────
@router.post(
    "/resources",
    response_model=TutorResourceResponse,
    status_code=201,
    summary="Share a new resource with course students [TRAINER or ADMIN]",
)
async def create_resource(
    body:         TutorResourceCreate,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> TutorResourceResponse:
    if current_user.role not in (UserRole.TRAINER, UserRole.ADMIN):
        raise HTTPException(403, "Trainer or admin privileges required.")
    svc = TutorResourceService(db)
    try:
        r = await svc.create(body, tutor=current_user)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return TutorResourceResponse.from_orm(r)


# ── PATCH /resources/{id}  🔒🛡 trainer (own) or admin ───────────────────────
@router.patch(
    "/resources/{resource_id}",
    response_model=TutorResourceResponse,
    summary="Update a resource [TRAINER (own) or ADMIN]",
)
async def update_resource(
    resource_id:  int,
    body:         TutorResourceUpdate,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> TutorResourceResponse:
    svc = TutorResourceService(db)
    r   = await svc.get_by_id(resource_id)
    if r is None:
        raise HTTPException(404, "Resource not found.")
    if current_user.role not in (UserRole.TRAINER, UserRole.ADMIN):
        raise HTTPException(403, "Trainer or admin privileges required.")
    if current_user.role == UserRole.TRAINER and r.tutor_id != current_user.id:
        raise HTTPException(403, "You can only edit your own resources.")
    updated = await svc.update(r, body)
    return TutorResourceResponse.from_orm(updated)


# ── DELETE /resources/{id}  🔒🛡 trainer (own) or admin ──────────────────────
@router.delete(
    "/resources/{resource_id}",
    status_code=204,
    summary="Soft-delete a resource [TRAINER (own) or ADMIN]",
)
async def delete_resource(
    resource_id:  int,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> None:
    svc = TutorResourceService(db)
    r   = await svc.get_by_id(resource_id)
    if r is None:
        raise HTTPException(404, "Resource not found.")
    if current_user.role not in (UserRole.TRAINER, UserRole.ADMIN):
        raise HTTPException(403, "Trainer or admin privileges required.")
    if current_user.role == UserRole.TRAINER and r.tutor_id != current_user.id:
        raise HTTPException(403, "You can only delete your own resources.")
    await svc.delete(r)