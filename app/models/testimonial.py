"""
app/models/testimonial.py
==========================
Testimonial ORM model.
"""

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Testimonial(Base, TimestampMixin):
    """
    Stores graduate/student testimonials shown on the public site.
    """
    __tablename__ = "testimonials"

    id:      Mapped[int] = mapped_column(primary_key=True, index=True)

    # Optional FK — a registered user submitting their own testimonial
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Display fields (always stored, even for anonymous submissions)
    name:       Mapped[str]           = mapped_column(String(150), nullable=False)
    role:       Mapped[str]           = mapped_column(String(200), nullable=False)  # e.g. "Java Dev @ Fidelity Bank"
    course:     Mapped[str]           = mapped_column(String(200), nullable=False)  # course name string
    avatar:     Mapped[Optional[str]] = mapped_column(String(10),  nullable=True)   # 2-char initials or emoji
    country:    Mapped[Optional[str]] = mapped_column(String(5),   nullable=True)   # flag emoji e.g. "🇬🇭"
    rating:     Mapped[int]           = mapped_column(Integer, default=5)           # 1-5 stars
    text:       Mapped[str]           = mapped_column(Text, nullable=False)

    # Moderation
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[Optional["User"]] = relationship()

    def __repr__(self) -> str:
        return f"<Testimonial id={self.id} name={self.name} approved={self.is_approved}>"