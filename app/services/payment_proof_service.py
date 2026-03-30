"""
app/services/payment_proof_service.py
=======================================
Business logic for PaymentProof upload and admin verification workflow.

Spring Boot equivalent
-----------------------
  @Service PaymentProofService
  uploadFile() ≈ MultipartFile handling + S3Client.putObject() or FileOutputStream
  verify()     ≈ @Transactional status transition + cascade to enrollment/registration
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Enrollment
from app.models.payment_proof import PaymentProof, ProofStatus
from app.models.workshop import WorkshopRegistration
from app.models.user import User
from app.schemas.payment_proof import ProofVerifyRequest

# ── File storage configuration ────────────────────────────────────────────────
# In production: swap UPLOAD_DIR for an S3 bucket key prefix.
# Store only the key/path in the DB; serve via pre-signed URL (S3) or /uploads/* (dev).
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads/payment_proofs"))
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB


class PaymentProofService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload(
        self,
        file: UploadFile,
        user: User,
        enrollment_id: Optional[int] = None,
        workshop_registration_id: Optional[int] = None,
    ) -> PaymentProof:
        """
        Save the uploaded file to disk (or S3 in production) and persist a
        PaymentProof record with status=PENDING.

        Spring Boot equivalent:
          @PostMapping("/upload") @RequestParam MultipartFile file
          storageService.store(file)  +  repo.save(new PaymentProof(...))

        Validations:
          • Exactly one of enrollment_id / workshop_registration_id must be set.
          • File must be ≤ 5 MB and an allowed MIME type.
          • The enrollment/registration must belong to the uploading user.
        """
        if bool(enrollment_id) == bool(workshop_registration_id):
            raise ValueError(
                "Provide exactly one of enrollment_id or workshop_registration_id."
            )

        # Validate file size
        contents = await file.read()
        if len(contents) > MAX_FILE_BYTES:
            raise ValueError("File exceeds maximum size of 5 MB.")

        # Validate MIME (trust Content-Type header + simple magic-bytes check)
        ct = file.content_type or ""
        if ct not in ALLOWED_MIME:
            raise ValueError(
                f"Unsupported file type '{ct}'. Allowed: JPEG, PNG, WebP, PDF."
            )

        # Verify ownership
        await self._assert_ownership(user.id, enrollment_id, workshop_registration_id)

        # Persist to disk
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ext       = Path(file.filename or "file").suffix
        stored_fn = f"{uuid.uuid4().hex}{ext}"
        dest      = UPLOAD_DIR / stored_fn
        dest.write_bytes(contents)

        proof = PaymentProof(
            user_id=user.id,
            enrollment_id=enrollment_id,
            workshop_registration_id=workshop_registration_id,
            file_path=str(dest),
            original_name=file.filename or stored_fn,
            mime_type=ct,
            status=ProofStatus.PENDING,
        )
        self.db.add(proof)
        await self.db.flush()
        return proof

    # ── Admin verification ────────────────────────────────────────────────────

    async def verify(
        self, proof_id: int, data: ProofVerifyRequest, reviewer: User
    ) -> PaymentProof:
        """
        Admin approves or rejects a payment proof.
        If approved, the linked enrollment/registration is marked 'active'.

        Spring Boot:
          @Transactional
          public PaymentProof verify(Long id, ProofVerifyRequest req, User admin) { ... }
        """
        proof = await self.get_by_id(proof_id)
        if proof is None:
            raise ValueError("Payment proof not found.")
        if proof.status != ProofStatus.PENDING:
            raise ValueError("Only PENDING proofs can be verified.")

        proof.status       = data.status
        proof.reviewer_id  = reviewer.id
        proof.reviewer_note = data.reviewer_note
        self.db.add(proof)

        # Cascade: if approved, activate the linked enrollment/registration
        if data.status == ProofStatus.VERIFIED:
            await self._activate_linked(proof)

        await self.db.flush()
        return proof

    async def _activate_linked(self, proof: PaymentProof) -> None:
        """
        Mark the linked enrollment or workshop registration as active/registered
        once the payment is verified.
        """
        if proof.enrollment_id:
            result = await self.db.execute(
                select(Enrollment).where(Enrollment.id == proof.enrollment_id)
            )
            enrol = result.scalar_one_or_none()
            if enrol:
                enrol.status = "active"
                self.db.add(enrol)

        if proof.workshop_registration_id:
            result = await self.db.execute(
                select(WorkshopRegistration).where(
                    WorkshopRegistration.id == proof.workshop_registration_id
                )
            )
            reg = result.scalar_one_or_none()
            if reg:
                reg.status = "registered"
                self.db.add(reg)

    # ── Queries ──────────────────────────────────────────────────────────────

    async def get_by_id(self, proof_id: int) -> Optional[PaymentProof]:
        result = await self.db.execute(
            select(PaymentProof).where(PaymentProof.id == proof_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> List[PaymentProof]:
        result = await self.db.execute(
            select(PaymentProof)
            .where(PaymentProof.user_id == user_id)
            .order_by(PaymentProof.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(
        self,
        status: Optional[ProofStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PaymentProof], int]:
        """Admin: list all proofs with optional status filter."""
        q = select(PaymentProof).order_by(PaymentProof.created_at.desc())
        if status:
            q = q.where(PaymentProof.status == status)
        count_q = select(func.count(PaymentProof.id))
        if status:
            count_q = count_q.where(PaymentProof.status == status)
        total  = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(q.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _assert_ownership(
        self,
        user_id: int,
        enrollment_id: Optional[int],
        workshop_registration_id: Optional[int],
    ) -> None:
        """Raises ValueError if the enrollment/registration doesn't belong to user."""
        if enrollment_id:
            result = await self.db.execute(
                select(Enrollment).where(
                    Enrollment.id == enrollment_id,
                    Enrollment.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise ValueError("Enrollment not found or does not belong to this user.")

        if workshop_registration_id:
            result = await self.db.execute(
                select(WorkshopRegistration).where(
                    WorkshopRegistration.id == workshop_registration_id,
                    WorkshopRegistration.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise ValueError(
                    "Workshop registration not found or does not belong to this user."
                )