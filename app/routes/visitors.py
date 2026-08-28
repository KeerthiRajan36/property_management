import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_staff
from app.exceptions import NotFoundError, ConflictError
from app.models.tenant import Tenant
from app.models.building import Unit
from app.models.visitor import Visitor, VisitorStatus
from app.models.user import User
from app.schemas.visitor import VisitorCreate, VisitorOut
from app.services.notification_service import notify_visitor_approval
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/visitors", tags=["Visitors"])


@router.post("", response_model=VisitorOut, status_code=status.HTTP_201_CREATED)
def create_visitor(
    payload: VisitorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(Tenant).filter(Tenant.id == payload.tenant_id, Tenant.is_deleted.is_(False)).first():
        raise NotFoundError("Tenant not found")
    if not db.query(Unit).filter(Unit.id == payload.unit_id, Unit.is_deleted.is_(False)).first():
        raise NotFoundError("Unit not found")

    visitor = Visitor(**payload.model_dump(), visitor_status=VisitorStatus.EXPECTED)
    db.add(visitor)
    db.commit()
    db.refresh(visitor)

    notify_visitor_approval(payload.tenant_id, payload.visitor_name)
    write_audit_log(db, current_user.id, "CREATE", "Visitor", visitor.id)
    return visitor


@router.get("", response_model=PaginatedResponse[VisitorOut])
def list_visitors(
    tenant_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    status_: Optional[VisitorStatus] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Maintains full visitor history for security staff (Level 9)."""
    query = db.query(Visitor)
    if tenant_id:
        query = query.filter(Visitor.tenant_id == tenant_id)
    if unit_id:
        query = query.filter(Visitor.unit_id == unit_id)
    if status_:
        query = query.filter(Visitor.visitor_status == status_)
    return paginate(query, Visitor, PageParams(page, limit, sort_by, sort_order))


@router.put("/{visitor_id}/checkin", response_model=VisitorOut)
def checkin_visitor(
    visitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if not visitor:
        raise NotFoundError("Visitor not found")
    if visitor.visitor_status != VisitorStatus.EXPECTED:
        raise ConflictError(f"Visitor is currently '{visitor.visitor_status.value}', cannot check in")
    visitor.visitor_status = VisitorStatus.CHECKED_IN
    visitor.entry_time = datetime.datetime.utcnow()
    db.commit()
    db.refresh(visitor)
    write_audit_log(db, current_user.id, "UPDATE", "Visitor", visitor.id, {"action": "checkin"})
    return visitor


@router.put("/{visitor_id}/checkout", response_model=VisitorOut)
def checkout_visitor(
    visitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if not visitor:
        raise NotFoundError("Visitor not found")
    if visitor.visitor_status != VisitorStatus.CHECKED_IN:
        raise ConflictError(f"Visitor is currently '{visitor.visitor_status.value}', cannot check out")
    visitor.visitor_status = VisitorStatus.CHECKED_OUT
    visitor.exit_time = datetime.datetime.utcnow()
    db.commit()
    db.refresh(visitor)
    write_audit_log(db, current_user.id, "UPDATE", "Visitor", visitor.id, {"action": "checkout"})
    return visitor
