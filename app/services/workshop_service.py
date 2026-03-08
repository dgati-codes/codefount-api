"""
app/services/workshop_service.py
=================================
Business logic for Workshops and Registrations.

Spring Boot equivalent
-----------------------
  @Service WorkshopService + @Service WorkshopRegistrationService
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workshop import Workshop, WorkshopRegistration
from app.schemas.workshop import WorkshopCreate, WorkshopUpdate


class WorkshopService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_workshops(
        self,
        free_only: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Workshop], int]:
        from sqlalchemy import func

        q = select(Workshop).where(Workshop.is_active == True)
        if free_only is True:
            q = q.where(Workshop.price == None)
        elif free_only is False:
            q = q.where(Workshop.price != None)

        from sqlalchemy import func
        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        result = await self.db.execute(q.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def get_by_id(self, workshop_id: int) -> Optional[Workshop]:
        result = await self.db.execute(
            select(Workshop).where(Workshop.id == workshop_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: WorkshopCreate) -> Workshop:
        workshop = Workshop(**data.model_dump())
        self.db.add(workshop)
        await self.db.flush()
        return workshop

    async def update(self, workshop: Workshop, data: WorkshopUpdate) -> Workshop:
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(workshop, k, v)
        self.db.add(workshop)
        await self.db.flush()
        return workshop

    async def delete(self, workshop: Workshop) -> None:
        workshop.is_active = False
        self.db.add(workshop)
        await self.db.flush()


class WorkshopRegistrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_registrations(self, user_id: int) -> List[WorkshopRegistration]:
        """
        Spring Boot: registrationRepository.findByUserId(userId)
        eager-loads Workshop.
        """
        result = await self.db.execute(
            select(WorkshopRegistration)
            .options(selectinload(WorkshopRegistration.workshop))
            .where(
                WorkshopRegistration.user_id == user_id,
                WorkshopRegistration.status == "registered",
            )
        )
        return list(result.scalars().all())

    async def register(self, user_id: int, workshop_id: int) -> WorkshopRegistration:
        """
        Creates registration and increments filled count atomically.
        Spring Boot: @Transactional — if either DB write fails, both roll back.
        """
        # Check duplicate
        existing = await self.db.execute(
            select(WorkshopRegistration).where(
                WorkshopRegistration.user_id == user_id,
                WorkshopRegistration.workshop_id == workshop_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already registered for this workshop")

        # Check seat availability
        ws_result = await self.db.execute(
            select(Workshop).where(Workshop.id == workshop_id)
        )
        workshop = ws_result.scalar_one_or_none()
        if workshop is None:
            raise ValueError("Workshop not found")
        if workshop.filled >= workshop.seats:
            raise ValueError("Workshop is fully booked")

        reg = WorkshopRegistration(user_id=user_id, workshop_id=workshop_id)
        self.db.add(reg)
        workshop.filled += 1
        self.db.add(workshop)
        await self.db.flush()
        return reg

    async def cancel(self, user_id: int, workshop_id: int) -> None:
        result = await self.db.execute(
            select(WorkshopRegistration).where(
                WorkshopRegistration.user_id == user_id,
                WorkshopRegistration.workshop_id == workshop_id,
            )
        )
        reg = result.scalar_one_or_none()
        if reg and reg.status == "registered":
            reg.status = "cancelled"
            self.db.add(reg)

            # Decrement filled count
            ws_result = await self.db.execute(
                select(Workshop).where(Workshop.id == workshop_id)
            )
            workshop = ws_result.scalar_one_or_none()
            if workshop and workshop.filled > 0:
                workshop.filled -= 1
                self.db.add(workshop)

            await self.db.flush()