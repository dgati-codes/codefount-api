"""
app/schemas/course.py
======================
Course, CurriculumItem, Enrollment Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# ── Curriculum ────────────────────────────────────────────────────────────────

class CurriculumItemBase(BaseModel):
    week:  str
    topic: str
    order: int = 0

class CurriculumItemCreate(CurriculumItemBase):
    pass

class CurriculumItemResponse(CurriculumItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Course ────────────────────────────────────────────────────────────────────

class CourseBase(BaseModel):
    title:      str
    category:   str
    trainer:    str
    duration:   str
    level:      str
    desc:       str
    outcome:    Optional[str] = None
    fee:        int
    offer:      int
    color:      str = "#0f766e"
    tag:        Optional[str] = None
    mode:       List[str] = []
    highlights: List[str] = []

class CourseCreate(CourseBase):
    curriculum: List[CurriculumItemCreate] = []

class CourseUpdate(BaseModel):
    title:      Optional[str] = None
    category:   Optional[str] = None
    trainer:    Optional[str] = None
    duration:   Optional[str] = None
    level:      Optional[str] = None
    desc:       Optional[str] = None
    outcome:    Optional[str] = None
    fee:        Optional[int] = None
    offer:      Optional[int] = None
    color:      Optional[str] = None
    tag:        Optional[str] = None
    mode:       Optional[List[str]] = None
    highlights: Optional[List[str]] = None
    is_active:  Optional[bool] = None

class CourseResponse(CourseBase):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    is_active:  bool
    curriculum: List[CurriculumItemResponse] = []

class CourseSummary(BaseModel):
    """Lightweight — used in lists"""
    model_config = ConfigDict(from_attributes=True)
    id:       int
    title:    str
    category: str
    trainer:  str
    fee:      int
    offer:    int
    color:    str
    tag:      Optional[str]
    duration: str
    level:    str
    mode:     List[str]


# ── Enrollment ────────────────────────────────────────────────────────────────

class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:        int
    course_id: int
    status:    str
    progress:  int
    course:    CourseSummary