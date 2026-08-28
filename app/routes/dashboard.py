from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin_or_manager
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service
from app.services.report_service import build_excel_report

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    return dashboard_service.get_summary(db)


@router.get("/reports/monthly-rent-collection")
def monthly_rent_collection(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)):
    return dashboard_service.report_monthly_rent_collection(db)


@router.get("/reports/property-wise-revenue")
def property_wise_revenue(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)):
    return dashboard_service.report_property_wise_revenue(db)


@router.get("/reports/unit-occupancy")
def unit_occupancy(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)):
    return dashboard_service.report_unit_occupancy(db)


@router.get("/reports/maintenance-expense")
def maintenance_expense(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)):
    return dashboard_service.report_maintenance_expense(db)


@router.get("/reports/utility-consumption")
def utility_consumption(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)):
    return dashboard_service.report_utility_consumption(db)


@router.get("/reports/tenant-payment-history/{tenant_id}")
def tenant_payment_history(
    tenant_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)
):
    rows = dashboard_service.report_tenant_payment_history(db, tenant_id)
    return [
        {
            "id": p.id,
            "invoice_id": p.invoice_id,
            "amount_paid": p.amount_paid,
            "payment_method": p.payment_method,
            "payment_date": p.payment_date,
        }
        for p in rows
    ]


@router.get("/reports/lease-expiry")
def lease_expiry(
    days_ahead: int = 30, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)
):
    rows = dashboard_service.report_lease_expiry(db, days_ahead)
    return [
        {
            "id": l.id,
            "tenant_id": l.tenant_id,
            "unit_id": l.unit_id,
            "end_date": l.end_date,
            "lease_status": l.lease_status.value,
        }
        for l in rows
    ]


@router.get("/reports/unit-occupancy/export")
def export_unit_occupancy_excel(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_manager)
):
    """Bonus feature: Excel export of a report."""
    data = dashboard_service.report_unit_occupancy(db)
    rows = [(row["status"], row["count"]) for row in data]
    excel_bytes = build_excel_report("Unit Occupancy", ["Status", "Count"], rows)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=unit_occupancy_report.xlsx"},
    )
