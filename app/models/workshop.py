"""
app/models/workshop.py
=======================
Workshop and WorkshopRegistration ORM models.
"""

from typing import List, Optional
from sqlalchemy import ARRAY, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Workshop(Base, TimestampMixin):
    __tablename__ = "workshops"

    id:          Mapped[int]           = mapped_column(primary_key=True, index=True)
    title:       Mapped[str]           = mapped_column(String(200), nullable=False)
    facilitator: Mapped[str]           = mapped_column(String(150), nullable=False)
    date:        Mapped[str]           = mapped_column(String(50),  nullable=False)
    time:        Mapped[str]           = mapped_column(String(60),  nullable=False)
    mode:        Mapped[str]           = mapped_column(String(80),  nullable=False)
    desc:        Mapped[str]           = mapped_column(Text, nullable=False)
    price:       Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # null = FREE
    seats:       Mapped[int]           = mapped_column(Integer, nullable=False)
    filled:      Mapped[int]           = mapped_column(Integer, default=0)
    color:       Mapped[str]           = mapped_column(String(20), default="#0f766e")
    icon:        Mapped[str]           = mapped_column(String(10), default="🎓")
    tag:         Mapped[str]           = mapped_column(String(20), default="FREE")
    is_active:   Mapped[bool]          = mapped_column(Boolean, default=True)

    agenda:        Mapped[List[str]]             = mapped_column(ARRAY(String), default=list)
    registrations: Mapped[List["WorkshopRegistration"]] = relationship(
        back_populates="workshop", cascade="all, delete-orphan"
    )

    @property
    def is_free(self) -> bool:
        return self.price is None or self.price == 0

    @property
    def seats_left(self) -> int:
        return self.seats - self.filled


class WorkshopRegistration(Base, TimestampMixin):
    __tablename__ = "workshop_registrations"
    __table_args__ = (
        UniqueConstraint("user_id", "workshop_id", name="uq_ws_registration"),
    )

    id:          Mapped[int] = mapped_column(primary_key=True)
    user_id:     Mapped[int] = mapped_column(ForeignKey("users.id",     ondelete="CASCADE"), nullable=False)
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False)
    status:      Mapped[str] = mapped_column(String(30), default="registered")  # registered | attended | cancelled

    user:     Mapped["User"]     = relationship(back_populates="workshop_registrations")
    workshop: Mapped["Workshop"] = relationship(back_populates="registrations")