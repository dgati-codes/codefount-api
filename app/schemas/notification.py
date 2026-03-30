"""
app/schemas/notification.py
============================
Pydantic schemas for Notification and UserNotification.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationTarget, NotificationType


# ── Request schemas ──────────────────────────────────────────────────────────

class NotificationCreate(BaseModel):
    title:            str
    body:             str
    ntype:            NotificationType    = NotificationType.INFO
    target:           NotificationTarget = NotificationTarget.ALL
    target_course_id: Optional[int]      = None   # required when target == COURSE
    target_user_id:   Optional[int]      = None   # required when target == USER


# ── Response schemas ─────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    title:            str
    body:             str
    ntype:            NotificationType
    target:           NotificationTarget
    target_course_id: Optional[int]
    created_at:       datetime


class UserNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int          # UserNotification.id
    is_read:    bool
    created_at: datetime

    # Flattened from the Notification relationship
    notification_id: int
    title:           str
    body:            str
    ntype:           str
    created_at:      datetime    # type: ignore[assignment]

    @classmethod
    def from_orm_delivery(cls, delivery) -> "UserNotificationResponse":
        n = delivery.notification
        return cls(
            id=delivery.id,
            is_read=delivery.is_read,
            created_at=delivery.created_at,
            notification_id=n.id,
            title=n.title,
            body=n.body,
            ntype=n.ntype,
        )


class MarkReadRequest(BaseModel):
    pass