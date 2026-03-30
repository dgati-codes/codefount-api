"""
app/models/resource.py
=======================
"""

import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ResourceType(str, enum.Enum):
    VIDEO    = "video"
    DOCUMENT = "document"
    LINK     = "link"


class TutorResource(Base, TimestampMixin):
    __tablename__ = "tutor_resources"

    id:        Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tutor_id:  Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    week:     Mapped[str]           = mapped_column(String(60),  nullable=False)   # "Wk 3–4"
    title:    Mapped[str]           = mapped_column(String(300), nullable=False)
    rtype:    Mapped[ResourceType]  = mapped_column(
        Enum(ResourceType, name="resourcetype"), default=ResourceType.VIDEO
    )

    # The two link fields the frontend exposes
    video_url:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # YouTube / Loom
    resource_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # Docs / GitHub / Drive

    is_active: Mapped[bool] = mapped_column(default=True)

    course: Mapped["Course"] = relationship()
    tutor:  Mapped["User"]   = relationship()

    def __repr__(self) -> str:
        return f"<TutorResource id={self.id} course={self.course_id} week={self.week!r}>"