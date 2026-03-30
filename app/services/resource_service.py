"""
app/services/resource_service.py
==================================
Business logic for TutorResource — tutor-shared learning materials.

Spring Boot equivalent
-----------------------
  @Service TutorResourceService { @Autowired TutorResourceRepository repo; ... }

  Access control rules (enforced at service layer, not just endpoint):
    • CREATE:   user must be TRAINER and assigned to the course (or ADMIN)
    • READ:     user must be enrolled in the course (or TRAINER/ADMIN)
    • UPDATE:   owning tutor or ADMIN
    • DELETE:   owning tutor or ADMIN
"""

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Enrollment
from app.models.resource import TutorResource
from app.models.user import User, UserRole
from app.schemas.resource import TutorResourceCreate, TutorResourceUpdate


class TutorResourceService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Queries ──────────────────────────────────────────────────────────────

    async def list_for_course(
        self, course_id: int, skip: int = 0, limit: int = 50
    ) -> Tuple[List[TutorResource], int]:
        """
        All active resources for a course, newest first.
        Called by enrolled students and by tutors.
        Spring Boot: repo.findByCourseIdAndIsActiveTrue(courseId, pageable)
        """
        q = (
            select(TutorResource)
            .options(selectinload(TutorResource.tutor), selectinload(TutorResource.course))
            .where(TutorResource.course_id == course_id, TutorResource.is_active == True)  # noqa: E712
            .order_by(TutorResource.created_at.desc())
        )
        total  = (await self.db.execute(
            select(func.count(TutorResource.id))
            .where(TutorResource.course_id == course_id, TutorResource.is_active == True)  # noqa: E712
        )).scalar_one()
        result = await self.db.execute(q.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def list_for_enrolled_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[TutorResource]:
        """
        All resources across all courses the user is currently enrolled in.
        This drives the student's Resources tab in Profile.

        Spring Boot:
          @Query("SELECT r FROM TutorResource r WHERE r.courseId IN
                  (SELECT e.courseId FROM Enrollment e WHERE e.userId=:uid AND e.status='active')
                  AND r.isActive=true ORDER BY r.createdAt DESC")
        """
        enrolled_course_ids_q = select(Enrollment.course_id).where(
            Enrollment.user_id == user_id,
            Enrollment.status == "active",
        )
        result = await self.db.execute(
            select(TutorResource)
            .options(selectinload(TutorResource.tutor), selectinload(TutorResource.course))
            .where(
                TutorResource.course_id.in_(enrolled_course_ids_q),
                TutorResource.is_active == True,  # noqa: E712
            )
            .order_by(TutorResource.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, rid: int) -> Optional[TutorResource]:
        result = await self.db.execute(
            select(TutorResource)
            .options(selectinload(TutorResource.tutor), selectinload(TutorResource.course))
            .where(TutorResource.id == rid)
        )
        return result.scalar_one_or_none()

    async def is_enrolled(self, user_id: int, course_id: int) -> bool:
        """Check if user has an active enrollment in course_id."""
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
                Enrollment.status == "active",
            )
        )
        return result.scalar_one_or_none() is not None

    # ── Commands ─────────────────────────────────────────────────────────────

    async def create(self, data: TutorResourceCreate, tutor: User) -> TutorResource:
        """
        Spring Boot: @PreAuthorize("hasAnyRole('TRAINER','ADMIN')") + repo.save(...)
        Raises ValueError if neither video_url nor resource_url is provided.
        """
        if not data.video_url and not data.resource_url:
            raise ValueError("At least one of video_url or resource_url must be provided.")

        r = TutorResource(
            course_id=data.course_id,
            tutor_id=tutor.id,
            week=data.week,
            title=data.title,
            rtype=data.rtype,
            video_url=data.video_url,
            resource_url=data.resource_url,
        )
        self.db.add(r)
        await self.db.flush()
        # Reload with relationships
        return await self.get_by_id(r.id)

    async def update(self, r: TutorResource, data: TutorResourceUpdate) -> TutorResource:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(r, field, value)
        self.db.add(r)
        await self.db.flush()
        return r

    async def delete(self, r: TutorResource) -> None:
        """Soft delete — set is_active=False."""
        r.is_active = False
        self.db.add(r)
        await self.db.flush()