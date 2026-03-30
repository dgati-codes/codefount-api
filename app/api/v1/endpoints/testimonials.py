"""
app/api/v1/endpoints/testimonials.py
========================================
Public testimonial listing + submission with optional profile photo upload.
Admin approval / management endpoints.

PUBLIC  (no token)  — GET list, POST submit (multipart/form-data)
AUTH    🔒          — POST /me  (links submission to user account)
ADMIN   🔒🛡         — GET /admin, PATCH approve/feature, DELETE
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.testimonial import (
    TestimonialAdminResponse,
    TestimonialCreate,
    TestimonialResponse,
    TestimonialUpdate,
)
from app.services.testimonial_service import TestimonialService

router = APIRouter(prefix="/testimonials", tags=["Testimonials"])

# ── Photo upload constraints ──────────────────────────────────────────────────
ALLOWED_IMG_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_BYTES  = 2 * 1024 * 1024   # 2 MB


async def _read_photo(
    photo: Optional[UploadFile],
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Validate and read an uploaded photo file.
    Returns (bytes, mime_type) or (None, None) if no file supplied.
    Raises HTTP 422 on type or size violations.
    """
    if photo is None or not photo.filename:
        return None, None
    ct = photo.content_type or ""
    if ct not in ALLOWED_IMG_MIME:
        raise HTTPException(422, f"Photo must be JPEG, PNG or WebP (got '{ct}').")
    data = await photo.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(422, "Photo must be under 2 MB.")
    return data, ct


# ── Public: list approved testimonials ──────────────────────────────────────
@router.get("", response_model=dict, summary="List approved testimonials (public)")
async def list_testimonials(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db:   AsyncSession = Depends(get_db),
) -> dict:
    svc          = TestimonialService(db)
    items, total = await svc.list_approved(skip=(page - 1) * size, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [TestimonialResponse.from_orm_with_photo(t) for t in items],
    }


# ── Public: submit (anonymous) via multipart ─────────────────────────────────
@router.post(
    "",
    response_model=TestimonialResponse,
    status_code=201,
    summary="Submit a testimonial as a guest (pending admin approval)",
)
async def submit_testimonial(
    name:    str           = Form(...,  description="Submitter full name"),
    role:    str           = Form(...,  description="Job title & company"),
    course:  str           = Form(...,  description="Course completed"),
    text:    str           = Form(...,  description="Testimonial body (≥ 10 chars)"),
    rating:  int           = Form(5,    ge=1, le=5),
    avatar:  Optional[str] = Form(None, description="2-char initials override"),
    country: Optional[str] = Form(None, description="Flag emoji e.g. 🇬🇭"),
    photo:   Optional[UploadFile] = File(None, description="Optional profile photo"),
    db:      AsyncSession  = Depends(get_db),
) -> TestimonialResponse:
    photo_data, photo_mime = await _read_photo(photo)
    body = TestimonialCreate(
        name=name, role=role, course=course,
        text=text, rating=rating, avatar=avatar, country=country,
    )
    svc = TestimonialService(db)
    t   = await svc.create(body, user=None, photo_data=photo_data, photo_mime=photo_mime)
    return TestimonialResponse.from_orm_with_photo(t)


# ── Authenticated: submit linked to account ───────────────────────────────────
@router.post(
    "/me",
    response_model=TestimonialResponse,
    status_code=201,
    summary="Submit a testimonial as an authenticated user 🔒",
)
async def submit_testimonial_auth(
    name:         str           = Form(...),
    role:         str           = Form(...),
    course:       str           = Form(...),
    text:         str           = Form(...),
    rating:       int           = Form(5, ge=1, le=5),
    avatar:       Optional[str] = Form(None),
    country:      Optional[str] = Form(None),
    photo:        Optional[UploadFile] = File(None),
    current_user: User          = Depends(get_current_active_user),
    db:           AsyncSession  = Depends(get_db),
) -> TestimonialResponse:
    photo_data, photo_mime = await _read_photo(photo)
    body = TestimonialCreate(
        name=name, role=role, course=course,
        text=text, rating=rating, avatar=avatar, country=country,
    )
    svc = TestimonialService(db)
    t   = await svc.create(body, user=current_user, photo_data=photo_data, photo_mime=photo_mime)
    return TestimonialResponse.from_orm_with_photo(t)


# ── Admin: list ALL (including unapproved) ────────────────────────────────────
@router.get(
    "/admin",
    response_model=dict,
    summary="List ALL testimonials including unapproved [ADMIN]",
)
async def list_all_testimonials(
    page:   int          = Query(1, ge=1),
    size:   int          = Query(50, ge=1, le=100),
    db:     AsyncSession = Depends(get_db),
    _admin: User         = Depends(require_admin),
) -> dict:
    svc          = TestimonialService(db)
    items, total = await svc.list_all(skip=(page - 1) * size, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [TestimonialAdminResponse.from_orm_with_photo(t) for t in items],
    }


# ── Admin: update / approve / feature ────────────────────────────────────────
@router.patch(
    "/{testimonial_id}",
    response_model=TestimonialResponse,
    summary="Update / approve / feature a testimonial [ADMIN]",
)
async def update_testimonial(
    testimonial_id: int,
    body:           TestimonialUpdate,
    db:             AsyncSession = Depends(get_db),
    _admin:         User         = Depends(require_admin),
) -> TestimonialResponse:
    svc = TestimonialService(db)
    t   = await svc.get_by_id(testimonial_id)
    if t is None:
        raise HTTPException(404, "Testimonial not found")
    updated = await svc.update(t, body)
    return TestimonialResponse.from_orm_with_photo(updated)


# ── Admin: delete ─────────────────────────────────────────────────────────────
@router.delete(
    "/{testimonial_id}",
    status_code=204,
    summary="Delete a testimonial [ADMIN]",
)
async def delete_testimonial(
    testimonial_id: int,
    db:             AsyncSession = Depends(get_db),
    _admin:         User         = Depends(require_admin),
) -> None:
    svc = TestimonialService(db)
    t   = await svc.get_by_id(testimonial_id)
    if t is None:
        raise HTTPException(404, "Testimonial not found")
    await svc.delete(t)