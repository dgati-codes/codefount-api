"""
app/services/testimonial_service.py
=====================================
Business logic for Testimonials with optional binary photo storage.

Spring Boot equivalent
-----------------------
  @Service TestimonialService
  Photo bytes stored as BYTEA in the testimonials table — no CDN needed for MVP.
  Admin must approve each submission before it appears publicly (is_approved=False by default).
"""
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.testimonial import Testimonial
from app.models.user import User
from app.schemas.testimonial import TestimonialCreate, TestimonialUpdate


class TestimonialService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Public listing ────────────────────────────────────────────────────────

    async def list_approved(
        self,
        featured_first: bool = True,
        skip:           int  = 0,
        limit:          int  = 50,
    ) -> Tuple[List[Testimonial], int]:
        """
        Public-facing list — only approved testimonials.
        Featured ones are shown first, then newest.

        Spring Boot:
          @Query("SELECT t FROM Testimonial t WHERE t.isApproved = true
                  ORDER BY t.isFeatured DESC, t.createdAt DESC")
          Page<Testimonial> findApproved(Pageable p)
        """
        base = select(Testimonial).where(Testimonial.is_approved == True)  # noqa: E712
        if featured_first:
            base = base.order_by(
                Testimonial.is_featured.desc(),
                Testimonial.created_at.desc(),
            )
        else:
            base = base.order_by(Testimonial.created_at.desc())

        count_q = select(func.count(Testimonial.id)).where(
            Testimonial.is_approved == True  # noqa: E712
        )
        total  = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(base.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    # ── Admin listing ─────────────────────────────────────────────────────────

    async def list_all(
        self,
        skip:  int = 0,
        limit: int = 100,
    ) -> Tuple[List[Testimonial], int]:
        """
        Admin view — all testimonials, pending ones first so they're easy to action.
        Spring Boot: repo.findAll(Sort.by("isApproved", "createdAt").descending())
        """
        total = (
            await self.db.execute(select(func.count(Testimonial.id)))
        ).scalar_one()
        result = await self.db.execute(
            select(Testimonial)
            .order_by(
                Testimonial.is_approved.asc(),    # pending (False) first
                Testimonial.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    # ── Single fetch ──────────────────────────────────────────────────────────

    async def get_by_id(self, tid: int) -> Optional[Testimonial]:
        result = await self.db.execute(
            select(Testimonial).where(Testimonial.id == tid)
        )
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        data:       TestimonialCreate,
        user:       Optional[User]  = None,
        photo_data: Optional[bytes] = None,
        photo_mime: Optional[str]   = None,
    ) -> Testimonial:
        
        # Validate photo size (e.g., max 5MB)
        if photo_data and len(photo_data) > 5 * 1024 * 1024:
            raise ValueError("Photo too large (max 5MB)")
    
        # Validate allowed MIME types
        if photo_mime and photo_mime not in ['image/jpeg', 'image/png', 'image/webp']:
            raise ValueError("Invalid image format")
        
        avatar_fallback = data.avatar
        if not avatar_fallback and data.name:
            parts = data.name.split()
            avatar_fallback = (
                "".join(p[0] for p in parts[:2]).upper()
                if len(parts) >= 2
                else data.name[:2].upper()
            )

        t = Testimonial(
            user_id         = user.id if user else None,
            name            = data.name.strip(),
            role            = data.role.strip(),
            course          = data.course.strip(),
            text            = data.text.strip(),
            rating          = data.rating,
            avatar          = avatar_fallback or "??",
            country         = data.country,
            photo_data      = photo_data,
            photo_mime_type = photo_mime,
            is_approved     = False,
            is_featured     = False,
        )
        self.db.add(t)
        await self.db.flush()
        return t

    # ── Update (admin) ────────────────────────────────────────────────────────

    async def update(self, t: Testimonial, data: TestimonialUpdate) -> Testimonial:
        """
        Partial update — only supplied (non-None) fields are applied.
        Supports approve / revoke / feature / unfeature.

        Spring Boot: BeanUtils.copyProperties(dto, entity, getNullFields(dto))
        """
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(t, field, value)
        self.db.add(t)
        await self.db.flush()
        return t

    # ── Delete (admin) ────────────────────────────────────────────────────────

    async def delete(self, t: Testimonial) -> None:
        """
        Hard delete — removes the row and the binary photo data with it.
        Spring Boot: repo.delete(entity)
        """
        await self.db.delete(t)