from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError, ConflictError
from app.models.building import Unit
from app.models.utility import UtilityReading, UtilityInvoice, UtilityType
from app.models.user import User
from app.schemas.utility import (
    UtilityReadingCreate,
    UtilityReadingOut,
    UtilityInvoiceCreate,
    UtilityInvoiceOut,
)
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/utilities", tags=["Utilities"])


@router.post("/readings", response_model=UtilityReadingOut, status_code=status.HTTP_201_CREATED)
def create_reading(
    payload: UtilityReadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    if not db.query(Unit).filter(Unit.id == payload.unit_id, Unit.is_deleted.is_(False)).first():
        raise NotFoundError("Unit not found")

    # current >= previous already validated in schema; compute derived fields here.
    units_consumed = payload.current_reading - payload.previous_reading

    reading = UtilityReading(
        unit_id=payload.unit_id,
        utility_type=payload.utility_type,
        previous_reading=payload.previous_reading,
        current_reading=payload.current_reading,
        units_consumed=units_consumed,
        rate=payload.rate,
        billing_month=payload.billing_month,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    write_audit_log(db, current_user.id, "CREATE", "UtilityReading", reading.id)
    return reading


@router.get("/readings", response_model=PaginatedResponse[UtilityReadingOut])
def list_readings(
    unit_id: Optional[int] = None,
    utility_type: Optional[UtilityType] = None,
    billing_month: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(UtilityReading)
    if unit_id:
        query = query.filter(UtilityReading.unit_id == unit_id)
    if utility_type:
        query = query.filter(UtilityReading.utility_type == utility_type)
    if billing_month:
        query = query.filter(UtilityReading.billing_month == billing_month)
    return paginate(query, UtilityReading, PageParams(page, limit, sort_by, sort_order))


@router.post("/invoices", response_model=UtilityInvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: UtilityInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    reading = db.query(UtilityReading).filter(UtilityReading.id == payload.reading_id).first()
    if not reading:
        raise NotFoundError("Utility reading not found")
    if db.query(UtilityInvoice).filter(UtilityInvoice.reading_id == reading.id).first():
        raise ConflictError("An invoice has already been generated for this reading")

    total_amount = reading.units_consumed * reading.rate
    invoice = UtilityInvoice(
        reading_id=reading.id,
        unit_id=reading.unit_id,
        utility_type=reading.utility_type,
        billing_month=reading.billing_month,
        units_consumed=reading.units_consumed,
        rate=reading.rate,
        total_amount=total_amount,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    write_audit_log(db, current_user.id, "CREATE", "UtilityInvoice", invoice.id)
    return invoice


@router.get("/invoices", response_model=PaginatedResponse[UtilityInvoiceOut])
def list_invoices(
    unit_id: Optional[int] = None,
    utility_type: Optional[UtilityType] = None,
    billing_month: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(UtilityInvoice)
    if unit_id:
        query = query.filter(UtilityInvoice.unit_id == unit_id)
    if utility_type:
        query = query.filter(UtilityInvoice.utility_type == utility_type)
    if billing_month:
        query = query.filter(UtilityInvoice.billing_month == billing_month)
    return paginate(query, UtilityInvoice, PageParams(page, limit, sort_by, sort_order))
