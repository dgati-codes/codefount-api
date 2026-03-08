"""app/schemas/workshop.py"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class WorkshopBase(BaseModel):
    title:       str
    facilitator: str
    date:        str
    time:        str
    mode:        str
    desc:        str
    price:       Optional[int] = None
    seats:       int
    color:       str = "#0f766e"
    icon:        str = "🎓"
    tag:         str = "FREE"
    agenda:      List[str] = []

class WorkshopCreate(WorkshopBase):
    pass

class WorkshopUpdate(BaseModel):
    title:       Optional[str] = None
    facilitator: Optional[str] = None
    date:        Optional[str] = None
    time:        Optional[str] = None
    mode:        Optional[str] = None
    desc:        Optional[str] = None
    price:       Optional[int] = None
    seats:       Optional[int] = None
    is_active:   Optional[bool] = None

class WorkshopResponse(WorkshopBase):
    model_config = ConfigDict(from_attributes=True)
    id:        int
    filled:    int
    is_active: bool

    @property
    def seats_left(self) -> int:
        return self.seats - self.filled

class WorkshopRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          int
    workshop_id: int
    status:      str
    workshop:    WorkshopResponse