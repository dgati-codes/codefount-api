"""
app/services/report_service.py
================================
Aggregation queries for the Admin Reports / Dashboard.

Spring Boot equivalent
-----------------------
  @Service AdminReportService
  All queries use scalar aggregations — no ORM entity loading needed.
  Spring equivalent: @Repository with @Query JPQL aggregates, or Criteria API.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import Integer, cast, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, Enrollment
from app.models.notification import UserNotification
from app.models.payment_proof import PaymentProof, ProofStatus
from app.models.user import User, UserRole
from app.models.workshop import Workshop
from app.schemas.misc import AdminDashboardStats, EnrollmentDataPoint, RevenueDataPoint


class ReportService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def dashboard(self) -> AdminDashboardStats:
        """
        Assembles the full admin dashboard payload in one call.
        Each stat is a separate aggregation query — fast with proper indexes.

        Spring Boot equivalent:
          AdminDashboardStats buildDashboard() {
            long students = userRepo.countByRole(STUDENT);
            long enrollments = enrollmentRepo.countByStatus("active");
            ...
          }
        """
        total_students = await self._count_students()
        active_enrols  = await self._count_active_enrollments()
        total_revenue  = await self._sum_revenue()
        pending_pay    = await self._count_pending_payments()
        workshops_act  = await self._count_active_workshops()
        courses_act    = await self._count_active_courses()
        unread_notifs  = await self._count_unread_notifications()
        revenue_series = await self._revenue_by_month()
        enrol_series   = await self._enrollment_by_course()

        return AdminDashboardStats(
            total_students=total_students,
            active_enrollments=active_enrols,
            total_revenue=total_revenue,
            pending_payments=pending_pay,
            workshops_active=workshops_act,
            placement_rate=95,      # static KPI — update when placement tracking is added
            courses_active=courses_act,
            unread_notifications=unread_notifs,
            revenue_by_month=revenue_series,
            enrollment_by_course=enrol_series,
        )

    # ── Individual aggregations ───────────────────────────────────────────────

    async def _count_students(self) -> int:
        """SELECT COUNT(*) FROM users WHERE role='student' AND is_active=true"""
        result = await self.db.execute(
            select(func.count(User.id)).where(
                User.role == UserRole.STUDENT,
                User.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one()

    async def _count_active_enrollments(self) -> int:
        result = await self.db.execute(
            select(func.count(Enrollment.id)).where(Enrollment.status == "active")
        )
        return result.scalar_one()

    async def _sum_revenue(self) -> int:
        """
        Revenue = SUM of course.offer for every VERIFIED payment proof tied to an enrollment.
        Falls back to SUM of offer for all active enrollments if no proofs exist yet.

        Spring Boot:
          @Query("SELECT COALESCE(SUM(c.offer), 0) FROM Enrollment e JOIN e.course c
                  JOIN PaymentProof p ON p.enrollmentId = e.id WHERE p.status='VERIFIED'")
        """
        # Verified proof revenue
        from app.models.course import Course as C
        result = await self.db.execute(
            select(func.coalesce(func.sum(C.offer), 0))
            .join(Enrollment, Enrollment.course_id == C.id)
            .join(PaymentProof, PaymentProof.enrollment_id == Enrollment.id)
            .where(PaymentProof.status == ProofStatus.VERIFIED)
        )
        verified_rev = result.scalar_one() or 0

        if verified_rev > 0:
            return int(verified_rev)

        # Fallback: estimate from all active enrollments (no proof system yet)
        result = await self.db.execute(
            select(func.coalesce(func.sum(C.offer), 0))
            .join(Enrollment, Enrollment.course_id == C.id)
            .where(Enrollment.status == "active")
        )
        return int(result.scalar_one() or 0)

    async def _count_pending_payments(self) -> int:
        result = await self.db.execute(
            select(func.count(PaymentProof.id)).where(
                PaymentProof.status == ProofStatus.PENDING
            )
        )
        return result.scalar_one()

    async def _count_active_workshops(self) -> int:
        result = await self.db.execute(
            select(func.count(Workshop.id)).where(Workshop.is_active == True)  # noqa: E712
        )
        return result.scalar_one()

    async def _count_active_courses(self) -> int:
        result = await self.db.execute(
            select(func.count(Course.id)).where(Course.is_active == True)  # noqa: E712
        )
        return result.scalar_one()

    async def _count_unread_notifications(self) -> int:
        result = await self.db.execute(
            select(func.count(UserNotification.id)).where(
                UserNotification.is_read == False  # noqa: E712
            )
        )
        return result.scalar_one()

    async def _revenue_by_month(self) -> List[RevenueDataPoint]:
        """
        Monthly revenue for the current year from verified payments.

        Spring Boot:
          @Query("SELECT MONTH(p.createdAt) as month, SUM(c.offer) as revenue
                  FROM PaymentProof p JOIN Enrollment e ON ... JOIN Course c ...
                  WHERE p.status='VERIFIED' AND YEAR(p.createdAt)=:year
                  GROUP BY MONTH(p.createdAt)")
        """
        current_year = datetime.now(timezone.utc).year
        from app.models.course import Course as C
        result = await self.db.execute(
            select(
                extract("month", PaymentProof.created_at).label("month_num"),
                func.sum(C.offer).label("revenue"),
            )
            .join(Enrollment, Enrollment.id == PaymentProof.enrollment_id)
            .join(C, C.id == Enrollment.course_id)
            .where(
                PaymentProof.status == ProofStatus.VERIFIED,
                extract("year", PaymentProof.created_at) == current_year,
            )
            .group_by("month_num")
            .order_by("month_num")
        )
        rows = result.all()

        MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        return [
            RevenueDataPoint(
                month=MONTH_NAMES[int(row.month_num) - 1],
                revenue=int(row.revenue),
            )
            for row in rows
        ]

    async def _enrollment_by_course(self) -> List[EnrollmentDataPoint]:
        """
        Count of active enrollments grouped by course title.

        Spring Boot:
          @Query("SELECT c.title, COUNT(e) FROM Enrollment e JOIN e.course c
                  WHERE e.status='active' GROUP BY c.title ORDER BY COUNT(e) DESC")
        """
        result = await self.db.execute(
            select(Course.title, func.count(Enrollment.id).label("cnt"))
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.status == "active")
            .group_by(Course.title)
            .order_by(func.count(Enrollment.id).desc())
            .limit(10)
        )
        return [
            EnrollmentDataPoint(course=row.title, count=row.cnt)
            for row in result.all()
        ]