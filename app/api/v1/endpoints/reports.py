"""
app/api/v1/endpoints/reports.py
=================================
Admin reports and analytics dashboard.

Spring Boot equivalent
-----------------------
  @RestController @RequestMapping("/api/v1/admin/reports") AdminReportController
  @PreAuthorize("hasRole('ADMIN')")  on every endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.misc import AdminDashboardStats
from app.services.report_service import ReportService

router = APIRouter(prefix="/admin/reports", tags=["Admin — Reports"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/admin/reports/dashboard    🔒🛡️ ADMIN
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/dashboard",
    response_model=AdminDashboardStats,
    summary="Full admin dashboard stats [ADMIN]",
)
async def dashboard(
    db:     AsyncSession = Depends(get_db),
    _admin: User         = Depends(require_admin),
) -> AdminDashboardStats:
    """
    Returns a single payload with all KPIs and chart data needed by the
    frontend Admin Reports tab.

    Spring Boot:
      @GetMapping("/dashboard")
      @PreAuthorize("hasRole('ADMIN')")
      AdminDashboardStats dashboard() { return reportService.dashboard(); }
    """
    svc = ReportService(db)
    return await svc.dashboard()