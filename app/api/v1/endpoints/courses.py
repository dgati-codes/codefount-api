"""
app/api/v1/endpoints/courses.py
================================

"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    CourseSummary,
    CourseUpdate,
    EnrollmentResponse,
)
from app.services.course_service import CourseService, EnrollmentService

router = APIRouter(prefix="/courses", tags=["Courses"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/courses          PUBLIC
# Spring Boot: @GetMapping  Page<CourseSummary> list(@RequestParam ...)
# Query params: ?category=DevOps&search=java&page=0&size=12
# ─────────────────────────────────────────────────────────────────────────────
@router.get("", response_model=dict, summary="List all active courses (public)")
async def list_courses(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title"),
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = CourseService(db)
    skip = (page - 1) * size
    courses, total = await svc.list_courses(category=category, search=search, skip=skip, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [CourseSummary.model_validate(c) for c in courses],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/courses/{id}     PUBLIC
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{course_id}", response_model=CourseResponse, summary="Get course detail (public)")
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    svc    = CourseService(db)
    course = await svc.get_by_id(course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return CourseResponse.model_validate(course)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/courses          ADMIN ONLY
# ─────────────────────────────────────────────────────────────────────────────
@router.post("", response_model=CourseResponse, status_code=201, summary="Create course [ADMIN]")
async def create_course(
    body:  CourseCreate,
    db:    AsyncSession = Depends(get_db),
    _admin: User        = Depends(require_admin),   # ≈ @PreAuthorize("hasRole('ADMIN')")
) -> CourseResponse:
    svc    = CourseService(db)
    course = await svc.create(body)
    return CourseResponse.model_validate(course)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/courses/{id}    ADMIN ONLY
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/{course_id}", response_model=CourseResponse, summary="Update course [ADMIN]")
async def update_course(
    course_id: int,
    body:      CourseUpdate,
    db:        AsyncSession = Depends(get_db),
    _admin:    User         = Depends(require_admin),
) -> CourseResponse:
    svc    = CourseService(db)
    course = await svc.get_by_id(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    updated = await svc.update(course, body)
    return CourseResponse.model_validate(updated)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/courses/{id}   ADMIN ONLY  (soft delete)
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{course_id}", status_code=204, summary="Soft-delete course [ADMIN]")
async def delete_course(
    course_id: int,
    db:        AsyncSession = Depends(get_db),
    _admin:    User         = Depends(require_admin),
) -> None:
    svc    = CourseService(db)
    course = await svc.get_by_id(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    await svc.delete(course)


enroll_router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


# GET /api/v1/enrollments/my     🔒 PROTECTED
@enroll_router.get("/my", response_model=List[EnrollmentResponse], summary="My enrollments")
async def my_enrollments(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[EnrollmentResponse]:
    svc         = EnrollmentService(db)
    enrollments = await svc.get_user_enrollments(current_user.id)
    return [EnrollmentResponse.model_validate(e) for e in enrollments]


# POST /api/v1/enrollments/{course_id}   🔒 PROTECTED
@enroll_router.post("/{course_id}", status_code=201, response_model=EnrollmentResponse, summary="Enroll in a course")
async def enroll(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    svc = EnrollmentService(db)
    try:
        enrollment = await svc.enroll(current_user.id, course_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    # reload with course relation
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.course import Enrollment, Course
    result = await db.execute(
        select(Enrollment)
        .options(selectinload(Enrollment.course))
        .where(Enrollment.id == enrollment.id)
    )
    return EnrollmentResponse.model_validate(result.scalar_one())


# DELETE /api/v1/enrollments/{course_id}  🔒 PROTECTED
@enroll_router.delete("/{course_id}", status_code=204, summary="Unenroll from a course")
async def unenroll(
    course_id:    int,
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> None:
    svc = EnrollmentService(db)
    await svc.unenroll(current_user.id, course_id)


# PATCH /api/v1/enrollments/{course_id}/progress   🔒 PROTECTED
@enroll_router.patch("/{course_id}/progress", status_code=204, summary="Update course progress")
async def update_progress(
    course_id:    int,
    progress:     int          = Query(..., ge=0, le=100),
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
) -> None:
    svc = EnrollmentService(db)
    await svc.update_progress(current_user.id, course_id, progress)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/courses/{course_id}/students    TRAINER or ADMIN
# Returns list of students enrolled in a course
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{course_id}/students",
    response_model=dict,
    summary="Students enrolled in a course [TRAINER or ADMIN]",
)
async def course_students(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.models.user import UserRole, User as UserModel
    from app.models.course import Enrollment
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    if current_user.role not in (UserRole.TRAINER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Trainer or admin required")

    result = await db.execute(
        select(Enrollment)
        .options(selectinload(Enrollment.user))
        .where(Enrollment.course_id == course_id)
    )
    enrollments = result.scalars().all()

    students = [
        {
            "id": e.user_id,
            "name": e.user.full_name if e.user else f"User #{e.user_id}",
            "email": e.user.email if e.user else "",
            "enrollment_id": e.id,
            "status": e.status,
            "progress": e.progress,
            "joined": e.created_at.isoformat() if e.created_at else None,
        }
        for e in enrollments
    ]
    return {"total": len(students), "items": students}
