"""
app/services/course_service.py
================================
Business logic for Courses and Enrollments.

Spring Boot equivalent
-----------------------
  @Service CourseService + @Service EnrollmentService
  Uses JPARepository-style patterns translated to async SQLAlchemy selects.
"""

from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CurriculumItem, Enrollment
from app.schemas.course import CourseCreate, CourseUpdate


class CourseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_courses(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Course], int]:
        """
        Spring Boot: Page<Course> findAll(Specification<Course> spec, Pageable pageable)
        Returns (items, total_count) for pagination.
        """
        q = (
            select(Course)
            .options(selectinload(Course.curriculum))  # ≈ @EntityGraph / JOIN FETCH
            .where(Course.is_active == True)
        )
        if category:
            q = q.where(Course.category == category)
        if search:
            q = q.where(Course.title.ilike(f"%{search}%"))

        total_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(total_q)).scalar_one()

        result  = await self.db.execute(q.offset(skip).limit(limit))
        courses = result.scalars().all()
        return list(courses), total

    async def get_by_id(self, course_id: int) -> Optional[Course]:
        """repo.findById(id)  — eager-loads curriculum"""
        result = await self.db.execute(
            select(Course)
            .options(selectinload(Course.curriculum))
            .where(Course.id == course_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CourseCreate) -> Course:
        """
        Saves course + curriculum items in one transaction.
        Spring Boot: @Transactional save() — cascaded to CurriculumItem.
        """
        curriculum_data = data.curriculum
        course = Course(
            **data.model_dump(exclude={"curriculum"}),
        )
        self.db.add(course)
        await self.db.flush()   # get course.id

        for i, item in enumerate(curriculum_data):
            ci = CurriculumItem(
                course_id=course.id,
                week=item.week,
                topic=item.topic,
                order=item.order or i,
            )
            self.db.add(ci)

        await self.db.flush()
        return course

    async def update(self, course: Course, data: CourseUpdate) -> Course:
        update_data = data.model_dump(exclude_none=True)
        for k, v in update_data.items():
            setattr(course, k, v)
        self.db.add(course)
        await self.db.flush()
        return course

    async def delete(self, course: Course) -> None:
        """Soft delete — Spring Boot: @SQLDelete(sql="UPDATE courses SET is_active=false ...")"""
        course.is_active = False
        self.db.add(course)
        await self.db.flush()


class EnrollmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_enrollments(self, user_id: int) -> List[Enrollment]:
        """
        Spring Boot: enrollmentRepository.findByUserId(userId)
        Eager-loads the related Course.
        """
        result = await self.db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.course).selectinload(Course.curriculum))
            .where(Enrollment.user_id == user_id, Enrollment.status == "active")
        )
        return list(result.scalars().all())

    async def enroll(self, user_id: int, course_id: int) -> Enrollment:
        """
        Creates enrollment or raises ValueError if duplicate.
        Spring Boot: @Transactional + check for existing record.
        """
        existing = await self.db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already enrolled in this course")

        enrollment = Enrollment(user_id=user_id, course_id=course_id)
        self.db.add(enrollment)
        await self.db.flush()
        return enrollment

    async def unenroll(self, user_id: int, course_id: int) -> None:
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
            )
        )
        enrollment = result.scalar_one_or_none()
        if enrollment:
            enrollment.status = "withdrawn"
            self.db.add(enrollment)
            await self.db.flush()

    async def update_progress(self, user_id: int, course_id: int, progress: int) -> None:
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id,
            )
        )
        enrollment = result.scalar_one_or_none()
        if enrollment:
            enrollment.progress = min(max(progress, 0), 100)
            self.db.add(enrollment)
            await self.db.flush()