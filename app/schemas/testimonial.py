"""
app/schemas/testimonial.py
===========================
Pydantic schemas for Testimonial.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ──────────────────────────────────────────────────────────

class TestimonialCreate(BaseModel):
    name:    str
    role:    str             = Field(..., description="Job title and company e.g. 'Java Dev @ Fidelity Bank'")
    course:  str             = Field(..., description="Course name string")
    text:    str             = Field(..., min_length=20)
    rating:  int             = Field(5, ge=1, le=5)
    avatar:  Optional[str]   = None   # 2-char initials
    country: Optional[str]   = None   # flag emoji


class TestimonialUpdate(BaseModel):
    is_approved: Optional[bool] = None
    is_featured: Optional[bool] = None
    name:        Optional[str]  = None
    role:        Optional[str]  = None
    text:        Optional[str]  = None
    rating:      Optional[int]  = Field(None, ge=1, le=5)


# ── Response schemas ─────────────────────────────────────────────────────────

class TestimonialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          int
    name:        str
    role:        str
    course:      str
    text:        str
    rating:      int
    avatar:      Optional[str]
    country:     Optional[str]
    is_approved: bool
    is_featured: bool


class TestimonialAdminResponse(TestimonialResponse):
    user_id: Optional[int]