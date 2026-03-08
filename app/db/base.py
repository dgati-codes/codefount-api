"""
app/db/base.py
===============
Declarative base + shared mixin.

Spring Boot equivalent
-----------------------
  @Entity base class / @MappedSuperclass with @Id, @CreatedDate, @LastModifiedDate
  (via Spring Data JPA Auditing).
  SQLAlchemy's DeclarativeBase  ≈  javax.persistence.@Entity + @Table.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    All ORM models inherit from this.
    Spring Boot equivalent: abstract @MappedSuperclass BaseEntity
    """
    pass


class TimestampMixin:
    """
    Automatically set created_at / updated_at.
    Spring Boot equivalent:
      @CreatedDate  LocalDateTime createdAt;
      @LastModifiedDate  LocalDateTime updatedAt;
      + @EntityListeners(AuditingEntityListener.class)
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )