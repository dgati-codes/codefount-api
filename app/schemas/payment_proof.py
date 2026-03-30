"""
app/schemas/payment_proof.py
==============================
Pydantic schemas for PaymentProof.

Response shapes:
  PaymentProofResponse         — returned to the uploading student
  PaymentProofAdminResponse    — enriched with student name/email and course title
  ProofVerifyRequest           — admin approve / reject body

Spring Boot equivalent: PaymentProofResponse.java, ProofVerifyRequest.java DTOs
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.payment_proof import ProofStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class ProofVerifyRequest(BaseModel):
    """Admin approve / reject body. PATCH /payment-proofs/admin/{id}/verify"""
    status:        ProofStatus
    reviewer_note: Optional[str] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class PaymentProofResponse(BaseModel):
    """
    Minimal response — safe to return to the uploading student.
    Does NOT include file_data (bytes would be massive).
    """
    model_config = ConfigDict(from_attributes=True)

    id:                       int
    user_id:                  int
    enrollment_id:            Optional[int]
    workshop_registration_id: Optional[int]
    original_name:            str
    mime_type:                Optional[str]
    file_size:                Optional[int]
    status:                   ProofStatus
    reviewer_note:            Optional[str]
    created_at:               datetime


class PaymentProofAdminResponse(PaymentProofResponse):
    """
    Extended response for the admin Payments tab.
    Includes denormalized student info and course title for display without
    requiring the frontend to make additional lookup requests.

    Spring Boot: AdminPaymentProofResponse DTO populated by a projection query
    or by manual enrichment in the service layer.
    """
    reviewer_id:   Optional[int] = None
    student_name:  Optional[str] = None
    student_email: Optional[str] = None
    course_title:  Optional[str] = None

    @classmethod
    def from_orm_full(cls, proof) -> "PaymentProofAdminResponse":
        """
        Enrich the base response with relationship data.
        Relationships must be eager-loaded before calling this method
        (PaymentProofService.get_by_id / list_all use selectinload).

        Spring Boot: ModelMapper with custom PropertyMap, or a @Service method
        that manually populates the DTO from the fetched entity graph.
        """
        data = cls.model_validate(proof)
        if proof.user:
            data.student_name  = proof.user.full_name
            data.student_email = proof.user.email
        if (
            proof.enrollment
            and hasattr(proof.enrollment, "course")
            and proof.enrollment.course
        ):
            data.course_title = proof.enrollment.course.title
        return data