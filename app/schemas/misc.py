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

class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:     int
    course: str
    date:   str
    time:   str

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