"""
app/models/payment_proof.py
=============================

"""

import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProofStatus(str, enum.Enum):
    PENDING  = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    PAID     = "paid"



class PaymentProof(Base, TimestampMixin):
    __tablename__ = "payment_proofs"

    id:      Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Linked to either an Enrollment OR a WorkshopRegistration ──────────────
    enrollment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    workshop_registration_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workshop_registrations.id", ondelete="CASCADE"), nullable=True, index=True
    )

    file_path:     Mapped[str]           = mapped_column(Text, nullable=False)
    original_name: Mapped[str]           = mapped_column(String(255), nullable=False)
    mime_type:     Mapped[Optional[str]] = mapped_column(String(80),  nullable=True)  # image/jpeg, application/pdf

    # ── Verification workflow ─────────────────────────────────────────────────
    status:          Mapped[ProofStatus]   = mapped_column(
        Enum(ProofStatus, name="proofstatus"), default=ProofStatus.PENDING
    )
    reviewer_id:     Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_note:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user:          Mapped["User"]                        = relationship(foreign_keys=[user_id])
    reviewer:      Mapped[Optional["User"]]              = relationship(foreign_keys=[reviewer_id])
    enrollment:    Mapped[Optional["Enrollment"]]        = relationship()
    workshop_reg:  Mapped[Optional["WorkshopRegistration"]] = relationship()

    def __repr__(self) -> str:
        return (
            f"<PaymentProof id={self.id} user={self.user_id} "
            f"status={self.status} file={self.original_name!r}>"
        )