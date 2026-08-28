import datetime

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ConflictError, BusinessRuleError
from app.models.lease import Lease
from app.models.rent import RentInvoice, Payment, InvoiceStatus
from app.schemas.rent import InvoiceGenerateRequest, PaymentCreate
from app.services.notification_service import notify_rent_due, notify_rent_overdue
from app.utils.audit import write_audit_log


def generate_invoice(db: Session, payload: InvoiceGenerateRequest, actor_id: int | None) -> RentInvoice:
    lease = db.query(Lease).filter(Lease.id == payload.lease_id, Lease.is_deleted.is_(False)).first()
    if not lease:
        raise NotFoundError("Lease not found")

    existing = (
        db.query(RentInvoice)
        .filter(RentInvoice.lease_id == lease.id, RentInvoice.billing_month == payload.billing_month)
        .first()
    )
    if existing:
        raise ConflictError(
            f"An invoice for lease {lease.id} / {payload.billing_month} already exists"
        )

    total_amount = lease.monthly_rent + payload.late_fee - payload.discount
    if total_amount < 0:
        raise BusinessRuleError("Discount cannot exceed rent + late fee")

    invoice = RentInvoice(
        lease_id=lease.id,
        billing_month=payload.billing_month,
        rent_amount=lease.monthly_rent,
        late_fee=payload.late_fee,
        discount=payload.discount,
        total_amount=total_amount,
        due_date=payload.due_date,
        status=InvoiceStatus.PENDING,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    write_audit_log(db, actor_id, "CREATE", "RentInvoice", invoice.id, {"lease_id": lease.id})
    notify_rent_due(lease.tenant_id, invoice.id, invoice.total_amount, str(invoice.due_date))
    return invoice


def refresh_overdue_statuses(db: Session) -> int:
    """Business rule: automatically identify overdue rent. Scans all pending
    invoices whose due_date has passed and flips them to Overdue."""
    today = datetime.date.today()
    pending = (
        db.query(RentInvoice)
        .filter(RentInvoice.status == InvoiceStatus.PENDING, RentInvoice.due_date < today)
        .all()
    )
    for invoice in pending:
        invoice.status = InvoiceStatus.OVERDUE
        lease = db.query(Lease).filter(Lease.id == invoice.lease_id).first()
        if lease:
            notify_rent_overdue(lease.tenant_id, invoice.id, invoice.total_amount)
    if pending:
        db.commit()
    return len(pending)


def pay_invoice(db: Session, invoice_id: int, payload: PaymentCreate, actor_id: int | None) -> Payment:
    invoice = db.query(RentInvoice).filter(RentInvoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError("Invoice not found")
    if invoice.status == InvoiceStatus.CANCELLED:
        raise BusinessRuleError("Cannot pay a cancelled invoice")
    if invoice.status == InvoiceStatus.PAID:
        raise ConflictError("Invoice has already been paid in full")

    already_paid = (
        db.query(Payment).filter(Payment.invoice_id == invoice.id).with_entities(Payment.amount_paid).all()
    )
    total_paid_so_far = sum(p[0] for p in already_paid)
    remaining = invoice.total_amount - total_paid_so_far

    if payload.amount_paid > remaining + 1e-6:
        raise BusinessRuleError(
            f"Payment ({payload.amount_paid}) exceeds the remaining invoice balance ({remaining})"
        )

    payment = Payment(
        invoice_id=invoice.id,
        amount_paid=payload.amount_paid,
        payment_method=payload.payment_method,
        remarks=payload.remarks,
    )
    db.add(payment)

    if total_paid_so_far + payload.amount_paid >= invoice.total_amount - 1e-6:
        invoice.status = InvoiceStatus.PAID

    db.commit()
    db.refresh(payment)
    write_audit_log(db, actor_id, "CREATE", "Payment", payment.id, {"invoice_id": invoice.id})
    return payment
