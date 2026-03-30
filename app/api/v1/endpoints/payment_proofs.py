"""
app/api/v1/endpoints/payment_proofs.py
=========================================
Proof-of-payment upload + admin verification.
Files are stored as raw bytes (BYTEA) in PostgreSQL — no S3 bucket needed.

Endpoints
---------
STUDENT  🔒    POST /payment-proofs/upload
               GET  /payment-proofs/me
ADMIN    🔒🛡   GET  /payment-proofs/admin
               GET  /payment-proofs/admin/{id}/view     ← streams binary file
               PATCH /payment-proofs/admin/{id}/verify

Spring Boot equivalent
-----------------------
  @RestController @RequestMapping("/api/v1/payment-proofs") PaymentProofController
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db, require_admin
from app.models.payment_proof import ProofStatus
from app.models.user import User
from app.schemas.payment_proof import (
    PaymentProofAdminResponse,
    PaymentProofResponse,
    ProofVerifyRequest,
)
from app.services.payment_proof_service import PaymentProofService

router = APIRouter(prefix="/payment-proofs", tags=["Payment Proofs"])


# ── Student: upload proof ─────────────────────────────────────────────────────
@router.post(
    "/upload",
    response_model=PaymentProofResponse,
    status_code=201,
    summary="Upload proof of payment (binary stored in DB) 🔒",
)
async def upload_proof(
    file:                     UploadFile       = File(..., description="PDF, JPEG, PNG or WebP — max 5 MB"),
    enrollment_id:            Optional[int]    = Query(None, description="Enrollment ID (provide this OR workshop_registration_id)"),
    workshop_registration_id: Optional[int]    = Query(None, description="Workshop Registration ID (provide this OR enrollment_id)"),
    current_user:             User             = Depends(get_current_active_user),
    db:                       AsyncSession     = Depends(get_db),
) -> PaymentProofResponse:
    """
    Accepts a file upload and stores the raw bytes in the payment_proofs table.
    Exactly ONE of enrollment_id / workshop_registration_id must be supplied.

    Spring Boot equivalent:
      @PostMapping("/upload") @PreAuthorize("isAuthenticated()")
      ResponseEntity<PaymentProofResponse> upload(
          @RequestParam MultipartFile file,
          @RequestParam Optional<Long> enrollmentId,
          @RequestParam Optional<Long> workshopRegistrationId,
          @AuthenticationPrincipal User user)
    """
    svc = PaymentProofService(db)
    try:
        proof = await svc.upload(
            file                     = file,
            user                     = current_user,
            enrollment_id            = enrollment_id,
            workshop_registration_id = workshop_registration_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PaymentProofResponse.model_validate(proof)


# ── Student: list own proofs ──────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=list,
    summary="My payment proofs 🔒",
)
async def my_proofs(
    current_user: User         = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
):
    svc   = PaymentProofService(db)
    items = await svc.list_for_user(current_user.id)
    return [PaymentProofResponse.model_validate(p) for p in items]


# ── Admin: list all proofs ────────────────────────────────────────────────────
@router.get(
    "/admin",
    response_model=dict,
    summary="List all payment proofs with optional status filter [ADMIN]",
)
async def list_all_proofs(
    status_filter: Optional[str] = Query(None, alias="status", description="pending|verified|rejected"),
    page:          int           = Query(1, ge=1),
    size:          int           = Query(20, ge=1, le=100),
    db:            AsyncSession  = Depends(get_db),
    _admin:        User          = Depends(require_admin),
) -> dict:
    svc     = PaymentProofService(db)
    pstatus = None
    if status_filter:
        try:
            pstatus = ProofStatus(status_filter)
        except ValueError:
            raise HTTPException(400, f"Invalid status '{status_filter}'. Use: pending, verified, rejected.")
    items, total = await svc.list_all(status=pstatus, skip=(page - 1) * size, limit=size)
    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": [PaymentProofAdminResponse.from_orm_full(p) for p in items],
    }


# ── Admin: view binary file inline ────────────────────────────────────────────
@router.get(
    "/admin/{proof_id}/view",
    summary="Stream the proof file inline (images/PDFs render in browser) [ADMIN]",
)
async def view_proof(
    proof_id: int,
    db:       AsyncSession = Depends(get_db),
    _admin:   User         = Depends(require_admin),
):
    """
    Returns the raw binary so the browser can render it inline.
    - Images open directly in an <img> tag.
    - PDFs open in the browser's built-in PDF viewer.

    The frontend fetches this as a Blob and creates a temporary object URL:
        const blob = await paymentProofs.viewBlob(id);
        const url  = URL.createObjectURL(blob);

    Spring Boot equivalent:
      @GetMapping("/admin/{id}/view")
      ResponseEntity<Resource> viewFile(@PathVariable Long id)
    """
    svc   = PaymentProofService(db)
    proof = await svc.get_by_id(proof_id)
    if proof is None:
        raise HTTPException(404, "Payment proof not found.")
    if not proof.file_data:
        raise HTTPException(
            404,
            "No binary data stored for this proof. The student may need to re-upload."
        )
    return Response(
        content    = proof.file_data,
        media_type = proof.mime_type or "application/octet-stream",
        headers    = {
            "Content-Disposition": f'inline; filename="{proof.original_name}"',
            "X-File-Name": proof.original_name,
            "X-File-Size": str(proof.file_size or len(proof.file_data)),
            # Allow admin to download the file directly if needed
            "Access-Control-Expose-Headers": "X-File-Name, X-File-Size",
        },
    )


# ── Admin: approve or reject ──────────────────────────────────────────────────
@router.patch(
    "/admin/{proof_id}/verify",
    response_model=PaymentProofAdminResponse,
    summary="Approve or reject a proof of payment [ADMIN]",
)
async def verify_proof(
    proof_id: int,
    body:     ProofVerifyRequest,
    db:       AsyncSession = Depends(get_db),
    admin:    User         = Depends(require_admin),
) -> PaymentProofAdminResponse:
    """
    On approval  → enrollment/workshop registration status set to 'active'/'registered'.
    On rejection → reviewer_note is stored so the student can see the reason.

    Spring Boot equivalent:
      @PatchMapping("/admin/{id}/verify")
      @PreAuthorize("hasRole('ADMIN')")
      @Transactional
      PaymentProofAdminResponse verify(@PathVariable Long id,
                                       @RequestBody ProofVerifyRequest body,
                                       @AuthenticationPrincipal User admin)
    """
    svc = PaymentProofService(db)
    try:
        proof = await svc.verify(proof_id, body, reviewer=admin)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return PaymentProofAdminResponse.from_orm_full(proof)