from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError
from app.models.rent import RentInvoice, Payment, InvoiceStatus
from app.models.user import User
from app.schemas.rent import InvoiceGenerateRequest, InvoiceOut, PaymentCreate, PaymentOut
from app.services import rent_service
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/rent", tags=["Rent & Payments"])


@router.post("/invoices/generate", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def generate_invoice(
    payload: InvoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    return rent_service.generate_invoice(db, payload, current_user.id)


@router.get("/invoices", response_model=PaginatedResponse[InvoiceOut])
def list_invoices(
    lease_id: Optional[int] = None,
    billing_month: Optional[str] = None,
    status_: Optional[InvoiceStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    rent_service.refresh_overdue_statuses(db)

    query = db.query(RentInvoice)
    if lease_id:
        query = query.filter(RentInvoice.lease_id == lease_id)
    if billing_month:
        query = query.filter(RentInvoice.billing_month == billing_month)
    if status_:
        query = query.filter(RentInvoice.status == status_)
    if date_from:
        query = query.filter(RentInvoice.due_date >= date_from)
    if date_to:
        query = query.filter(RentInvoice.due_date <= date_to)
    return paginate(query, RentInvoice, PageParams(page, limit, sort_by, sort_order))


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(RentInvoice).filter(RentInvoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError("Invoice not found")
    return invoice


@router.post("/pay/{invoice_id}", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def pay_invoice(
    invoice_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rent_service.pay_invoice(db, invoice_id, payload, current_user.id)


@router.get("/payments", response_model=PaginatedResponse[PaymentOut])
def list_payments(
    invoice_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Payment)
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    return paginate(query, Payment, PageParams(page, limit, sort_by, sort_order))


@router.get("/invoices/{invoice_id}/receipt")
def download_receipt(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bonus feature: PDF rent receipt."""
    from fastapi.responses import Response
    from app.models.lease import Lease
    from app.models.building import Unit
    from app.models.tenant import Tenant
    from app.services.receipt_service import build_receipt_pdf

    invoice = db.query(RentInvoice).filter(RentInvoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError("Invoice not found")
    lease = db.query(Lease).filter(Lease.id == invoice.lease_id).first()
    tenant = db.query(Tenant).filter(Tenant.id == lease.tenant_id).first() if lease else None
    unit = db.query(Unit).filter(Unit.id == lease.unit_id).first() if lease else None

    pdf_bytes = build_receipt_pdf(
        invoice,
        tenant.full_name if tenant else "Unknown",
        unit.unit_number if unit else "Unknown",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=receipt_invoice_{invoice_id}.pdf"},
    )
