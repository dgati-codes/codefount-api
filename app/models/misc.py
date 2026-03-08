"""
app/models/misc.py
===================
Service, Schedule, Enquiry ORM models.
"""

from typing import List, Optional
from sqlalchemy import ARRAY, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id:       Mapped[int]  = mapped_column(primary_key=True)
    icon:     Mapped[str]  = mapped_column(String(10), nullable=False)
    color:    Mapped[str]  = mapped_column(String(20), nullable=False)
    title:    Mapped[str]  = mapped_column(String(150), nullable=False)
    tag:      Mapped[str]  = mapped_column(String(60),  nullable=False)
    desc:     Mapped[str]  = mapped_column(Text, nullable=False)
    features: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    order:    Mapped[int]  = mapped_column(Integer, default=0)


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"

    id:     Mapped[int] = mapped_column(primary_key=True)
    course: Mapped[str] = mapped_column(String(200), nullable=False)
    date:   Mapped[str] = mapped_column(String(30),  nullable=False)
    time:   Mapped[str] = mapped_column(String(30),  nullable=False)


class Enquiry(Base, TimestampMixin):
    __tablename__ = "enquiries"

    id:      Mapped[int]           = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name:    Mapped[str]           = mapped_column(String(150), nullable=False)
    email:   Mapped[str]           = mapped_column(String(255), nullable=False)
    phone:   Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    message: Mapped[str]           = mapped_column(Text, nullable=False)
    status:  Mapped[str]           = mapped_column(String(30), default="new")  # new|read|replied

    user: Mapped[Optional["User"]] = relationship(back_populates="enquiries")