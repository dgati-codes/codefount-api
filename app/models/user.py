"""
app/models/user.py
===================
User ORM model.

Spring Boot equivalent
-----------------------
  @Entity @Table(name="users") public class User implements UserDetails { ... }
  Mapped[str]  ≈  @Column(nullable=false) String field;
  Enum         ≈  @Enumerated(EnumType.STRING)
"""

import enum
from typing import List, Optional

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TRAINER = "trainer"
    ADMIN   = "admin"


class User(Base, TimestampMixin):
    """
    Spring Boot equivalent:
      @Entity @Table(name="users")
      public class User implements UserDetails
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Profile
    full_name:  Mapped[str]           = mapped_column(String(150), nullable=False)
    email:      Mapped[str]           = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone:      Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    gender:     Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Auth
    hashed_password: Mapped[str]  = mapped_column(Text, nullable=False)
    role:            Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), default=UserRole.STUDENT, nullable=False
    )
    is_active:  Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    enrollments:          Mapped[List["Enrollment"]]          = relationship(back_populates="user", cascade="all, delete-orphan")
    workshop_registrations: Mapped[List["WorkshopRegistration"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    enquiries:            Mapped[List["Enquiry"]]             = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"