"""
app/models/course.py
=====================
Course, CurriculumItem, Enrollment ORM models.

Spring Boot equivalent
-----------------------
  @Entity Course, @Entity CurriculumItem, @Entity Enrollment
  @OneToMany / @ManyToOne / @ManyToMany JPA relationships.
"""

from typing import List, Optional
from sqlalchemy import (
    ARRAY, Boolean, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    """
    Spring Boot: @Entity @Table(name="courses") public class Course
    """
    __tablename__ = "courses"

    id:        Mapped[int]  = mapped_column(primary_key=True, index=True)
    title:     Mapped[str]  = mapped_column(String(200), nullable=False, index=True)
    category:  Mapped[str]  = mapped_column(String(100), nullable=False, index=True)
    trainer:   Mapped[str]  = mapped_column(String(150), nullable=False)
    duration:  Mapped[str]  = mapped_column(String(60),  nullable=False)
    level:     Mapped[str]  = mapped_column(String(80),  nullable=False)
    desc:      Mapped[str]  = mapped_column(Text, nullable=False)
    outcome:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fee:   Mapped[int] = mapped_column(Integer, nullable=False)   # in GHS pesewas
    offer: Mapped[int] = mapped_column(Integer, nullable=False)

    color: Mapped[str]           = mapped_column(String(20), default="#0f766e")
    tag:   Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True)

    # Stored as PostgreSQL arrays (Spring Boot: @ElementCollection)
    mode:       Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    highlights: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Relationships
    curriculum:  Mapped[List["CurriculumItem"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CurriculumItem.order"
    )
    enrollments: Mapped[List["Enrollment"]]     = relationship(back_populates="course")

    def __repr__(self) -> str:
        return f"<Course id={self.id} title={self.title}>"


class CurriculumItem(Base):
    """
    Spring Boot: @Entity @Table(name="curriculum_items")
    @ManyToOne @JoinColumn(name="course_id") Course course;
    """
    __tablename__ = "curriculum_items"

    id:        Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    week:      Mapped[str] = mapped_column(String(30), nullable=False)
    topic:     Mapped[str] = mapped_column(String(200), nullable=False)
    order:     Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped["Course"] = relationship(back_populates="curriculum")


class Enrollment(Base, TimestampMixin):
    """
    Enrolment join table with extra columns (status, batch_date).
    Spring Boot: @Entity @Table with @UniqueConstraint({ "user_id", "course_id" })
    """
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_enrollment"),
    )

    id:         Mapped[int] = mapped_column(primary_key=True)
    user_id:    Mapped[int] = mapped_column(ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
    course_id:  Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    status:     Mapped[str] = mapped_column(String(30), default="active")    # active | completed | withdrawn
    progress:   Mapped[int] = mapped_column(Integer, default=0)              # 0-100%

    user:   Mapped["User"]   = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")