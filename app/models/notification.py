"""
app/models/notification.py
============================
Notification and UserNotification ORM models.
"""

import enum
from typing import List, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    INFO     = "info"
    SUCCESS  = "success"
    WARNING  = "warning"
    RESOURCE = "resource"   
    PAYMENT  = "payment"    
    SYSTEM   = "system"


class NotificationTarget(str, enum.Enum):
    ALL        = "all"          # every active student
    ENROLLED   = "enrolled"     # all currently enrolled students
    COURSE     = "course"       # students enrolled in a specific course
    TUTORS     = "tutors"       # all trainers
    USER       = "user"         # single specific user (user_id must be set)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id:        Mapped[int]           = mapped_column(primary_key=True, index=True)
    sender_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title:   Mapped[str] = mapped_column(String(200), nullable=False)
    body:    Mapped[str] = mapped_column(Text, nullable=False)

    ntype: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notificationtype"),
        default=NotificationType.INFO,
    )
    target: Mapped[NotificationTarget] = mapped_column(
        Enum(NotificationTarget, name="notificationtarget"),
        default=NotificationTarget.ALL,
    )
    # Populated when target == COURSE; stores course id as string for flexibility
    target_course_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    # Populated when target == USER
    target_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    sender:       Mapped[Optional["User"]] = relationship(foreign_keys=[sender_id])
    deliveries:   Mapped[List["UserNotification"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} title={self.title!r} target={self.target}>"


class UserNotification(Base, TimestampMixin):
    __tablename__ = "user_notifications"

    id:              Mapped[int]  = mapped_column(primary_key=True, index=True)
    notification_id: Mapped[int]  = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id:         Mapped[int]  = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notification: Mapped["Notification"]  = relationship(back_populates="deliveries")
    user:         Mapped["User"]          = relationship()

    def __repr__(self) -> str:
        return f"<UserNotification notif={self.notification_id} user={self.user_id} read={self.is_read}>"