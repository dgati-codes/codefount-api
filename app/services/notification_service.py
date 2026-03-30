"""
app/services/notification_service.py
======================================
Business logic for Notifications (broadcast + per-user inbox).

Spring Boot equivalent
-----------------------
  @Service NotificationService
  fanout()  ≈  @Async void fanout(Notification n) — builds UserNotification rows
               for every target recipient in one transactional batch.

  The fanout is synchronous here (async SQLAlchemy) for simplicity.
  Production improvement: replace with a Celery/ARQ background task to avoid
  blocking the HTTP response for large recipient lists (Spring: @Async + ThreadPoolTaskExecutor).
"""

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Enrollment
from app.models.notification import (
    Notification, NotificationTarget, UserNotification,
)
from app.models.user import User, UserRole
from app.schemas.notification import NotificationCreate


class NotificationService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Fanout ────────────────────────────────────────────────────────────────

    async def broadcast(
        self, data: NotificationCreate, sender: User
    ) -> Notification:
        """
        1. Persist the Notification record.
        2. Resolve recipient user_ids based on target.
        3. Bulk-insert UserNotification rows (one per recipient).

        Spring Boot equivalent:
          @Transactional Notification broadcast(NotificationCreate dto, User sender) {
            Notification n = repo.save(new Notification(...));
            List<Long> ids = resolveRecipients(dto);
            ids.forEach(uid -> userNotifRepo.save(new UserNotification(n, uid)));
            return n;
          }
        """
        notif = Notification(
            sender_id=sender.id,
            title=data.title,
            body=data.body,
            ntype=data.ntype,
            target=data.target,
            target_course_id=data.target_course_id,
            target_user_id=data.target_user_id,
        )
        self.db.add(notif)
        await self.db.flush()   # get notif.id before creating deliveries

        recipient_ids = await self._resolve_recipients(data)
        for uid in recipient_ids:
            self.db.add(UserNotification(notification_id=notif.id, user_id=uid))

        await self.db.flush()
        return notif

    async def _resolve_recipients(self, data: NotificationCreate) -> List[int]:
        """
        Maps NotificationTarget → list of user_id integers.

        Spring Boot: private List<Long> resolveRecipients(NotificationCreate dto) { ... }
        """
        target = data.target

        if target == NotificationTarget.USER:
            return [data.target_user_id] if data.target_user_id else []

        if target == NotificationTarget.TUTORS:
            result = await self.db.execute(
                select(User.id).where(
                    User.role == UserRole.TRAINER, User.is_active == True  # noqa: E712
                )
            )
            return list(result.scalars().all())

        if target == NotificationTarget.COURSE and data.target_course_id:
            # Only active enrolled students of that specific course
            result = await self.db.execute(
                select(Enrollment.user_id).where(
                    Enrollment.course_id == data.target_course_id,
                    Enrollment.status == "active",
                )
            )
            return list(result.scalars().all())

        if target == NotificationTarget.ENROLLED:
            # All users with at least one active enrollment
            result = await self.db.execute(
                select(Enrollment.user_id).where(
                    Enrollment.status == "active"
                ).distinct()
            )
            return list(result.scalars().all())

        # Default: NotificationTarget.ALL — every active student
        result = await self.db.execute(
            select(User.id).where(
                User.role == UserRole.STUDENT, User.is_active == True  # noqa: E712
            )
        )
        return list(result.scalars().all())

    # ── Student inbox ─────────────────────────────────────────────────────────

    async def get_user_inbox(
        self, user_id: int, unread_only: bool = False, skip: int = 0, limit: int = 50
    ) -> Tuple[List[UserNotification], int]:
        """
        Returns the student's notification inbox, newest first.
        Spring Boot: repo.findByUserIdOrderByCreatedAtDesc(userId, pageable)
        """
        from sqlalchemy.orm import selectinload
        q = (
            select(UserNotification)
            .options(selectinload(UserNotification.notification))
            .where(UserNotification.user_id == user_id)
        )
        if unread_only:
            q = q.where(UserNotification.is_read == False)  # noqa: E712
        q = q.order_by(UserNotification.created_at.desc())

        count_q = select(func.count(UserNotification.id)).where(
            UserNotification.user_id == user_id
        )
        if unread_only:
            count_q = count_q.where(UserNotification.is_read == False)  # noqa: E712

        total  = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(q.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def mark_read(self, delivery_id: int, user_id: int) -> Optional[UserNotification]:
        """
        Mark a single delivery as read.
        Spring Boot: repo.findByIdAndUserId(id, userId) + save(updated)
        """
        result = await self.db.execute(
            select(UserNotification).where(
                UserNotification.id == delivery_id,
                UserNotification.user_id == user_id,
            )
        )
        delivery = result.scalar_one_or_none()
        if delivery:
            delivery.is_read = True
            self.db.add(delivery)
            await self.db.flush()
        return delivery

    async def mark_all_read(self, user_id: int) -> int:
        """Bulk mark-all-read. Returns count of rows updated."""
        from sqlalchemy import update
        result = await self.db.execute(
            update(UserNotification)
            .where(UserNotification.user_id == user_id, UserNotification.is_read == False)  # noqa: E712
            .values(is_read=True)
        )
        return result.rowcount

    async def unread_count(self, user_id: int) -> int:
        """Fast unread count — used by the navbar badge."""
        result = await self.db.execute(
            select(func.count(UserNotification.id)).where(
                UserNotification.user_id == user_id,
                UserNotification.is_read == False,  # noqa: E712
            )
        )
        return result.scalar_one()

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def list_sent(
        self, sender_id: Optional[int] = None, skip: int = 0, limit: int = 50
    ) -> Tuple[List[Notification], int]:
        """Admin: list all sent notifications, optionally filtered by sender."""
        q = select(Notification).order_by(Notification.created_at.desc())
        if sender_id:
            q = q.where(Notification.sender_id == sender_id)
        total  = (await self.db.execute(
            select(func.count(Notification.id))
        )).scalar_one()
        result = await self.db.execute(q.offset(skip).limit(limit))
        return list(result.scalars().all()), total