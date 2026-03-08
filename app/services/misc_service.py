"""
app/services/misc_service.py
=============================
Services, Schedules, Enquiries.
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.misc import Enquiry, Schedule, Service
from app.models.user import User
from app.schemas.misc import EnquiryCreate


class MiscService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Services ──────────────────────────────────────────────────────────────

    async def list_services(self) -> List[Service]:
        result = await self.db.execute(
            select(Service).order_by(Service.order)
        )
        return list(result.scalars().all())

    # ── Schedules ─────────────────────────────────────────────────────────────

    async def list_schedules(self) -> List[Schedule]:
        result = await self.db.execute(select(Schedule).order_by(Schedule.id))
        return list(result.scalars().all())

    # ── Enquiries ─────────────────────────────────────────────────────────────

    async def create_enquiry(
        self, data: EnquiryCreate, user: User | None = None
    ) -> Enquiry:
        """
        Any visitor can submit an enquiry; optionally linked to a user account.
        Spring Boot: save(new Enquiry(...)) — user_id nullable FK.
        """
        enquiry = Enquiry(
            user_id=user.id if user else None,
            name=data.name,
            email=data.email,
            phone=data.phone,
            subject=data.subject,
            message=data.message,
        )
        self.db.add(enquiry)
        await self.db.flush()
        return enquiry

    async def list_enquiries(self) -> List[Enquiry]:
        """Admin only."""
        result = await self.db.execute(
            select(Enquiry).order_by(Enquiry.created_at.desc())
        )
        return list(result.scalars().all())