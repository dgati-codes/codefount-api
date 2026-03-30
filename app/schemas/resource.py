"""
app/schemas/resource.py
========================
Pydantic schemas for TutorResource.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator

from app.models.resource import ResourceType


# ── Request schemas ──────────────────────────────────────────────────────────

class TutorResourceCreate(BaseModel):
    course_id:    int
    week:         str
    title:        str
    rtype:        ResourceType      = ResourceType.VIDEO
    video_url:    Optional[str]     = None   # YouTube / Loom / Vimeo
    resource_url: Optional[str]     = None   # Docs / GitHub / Google Drive

    @field_validator("video_url", "resource_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


class TutorResourceUpdate(BaseModel):
    week:         Optional[str]         = None
    title:        Optional[str]         = None
    rtype:        Optional[ResourceType] = None
    video_url:    Optional[str]         = None
    resource_url: Optional[str]         = None
    is_active:    Optional[bool]        = None

    @field_validator("video_url", "resource_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


# ── Response schemas ─────────────────────────────────────────────────────────

class TutorResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    course_id:    int
    tutor_id:     int
    week:         str
    title:        str
    rtype:        ResourceType
    video_url:    Optional[str]
    resource_url: Optional[str]
    is_active:    bool
    created_at:   datetime

    # Derived from relationship — populated via model_validate(instance)
    tutor_name:  Optional[str] = None
    course_title: Optional[str] = None

    @classmethod
    def from_orm(cls, obj) -> "TutorResourceResponse":
        data = cls.model_validate(obj)
        data.tutor_name   = obj.tutor.full_name  if obj.tutor  else None
        data.course_title = obj.course.title      if obj.course else None
        return data