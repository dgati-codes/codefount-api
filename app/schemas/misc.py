"""app/schemas/misc.py — Service, Schedule, Enquiry schemas"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:       int
    icon:     str
    color:    str
    title:    str
    tag:      str
    desc:     str
    features: List[str]
    order:    int


class ScheduleCreate(BaseModel):
    course: str
    date: str
    time: str
    mode: str = "Online"


class ScheduleUpdate(BaseModel):
    course: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    mode: Optional[str] = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:     int
    course: str
    date:   str
    time:   str
    mode: str = "Online"  # e-Learning | Classroom | Online


class ServiceCreate(BaseModel):
    icon: str
    color: str
    title: str
    tag: str = ""
    desc: str
    features: List[str] = []
    order: int = 0


class ServiceUpdate(BaseModel):
    icon: Optional[str] = None
    color: Optional[str] = None
    title: Optional[str] = None
    tag: Optional[str] = None
    desc: Optional[str] = None
    features: Optional[List[str]] = None
    order: Optional[int] = None


class EnquiryCreate(BaseModel):
    name:    str
    email:   EmailStr
    phone:   Optional[str] = None
    subject: Optional[str] = None
    message: str

class EnquiryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:      int
    name:    str
    email:   str
    subject: Optional[str]
    status:  str

# Generic paginated wrapper
class PaginatedResponse(BaseModel):
    total:   int
    page:    int
    size:    int
    items:   list

# ── Admin Reports ─────────────────────────────────────────────────────────────


class RevenueDataPoint(BaseModel):
    month: str
    revenue: int


class EnrollmentDataPoint(BaseModel):
    course: str
    count: int


class AdminDashboardStats(BaseModel):
    """
    Aggregated stats returned to the admin reports dashboard.
    Spring Boot: AdminDashboardStats DTO assembled by AdminReportService.
    """

    total_students: int
    active_enrollments: int
    total_revenue: int  # sum of offer prices for verified enrollments
    pending_payments: int
    workshops_active: int
    placement_rate: int
    courses_active: int
    unread_notifications: int
    revenue_by_month: List[RevenueDataPoint]
    enrollment_by_course: List[EnrollmentDataPoint]
