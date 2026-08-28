from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError
from app.models.lease import Lease, LeaseStatus
from app.models.user import User
from app.schemas.lease import LeaseCreate, LeaseUpdate, LeaseOut
from app.services import lease_service
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/leases", tags=["Leases"])


@router.post("", response_model=LeaseOut, status_code=status.HTTP_201_CREATED)
def create_lease(
    payload: LeaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    return lease_service.create_lease(db, payload, current_user.id)


@router.get("", response_model=PaginatedResponse[LeaseOut])
def list_leases(
    tenant_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    lease_status: Optional[LeaseStatus] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Lease).filter(Lease.is_deleted.is_(False))
    if tenant_id:
        query = query.filter(Lease.tenant_id == tenant_id)
    if unit_id:
        query = query.filter(Lease.unit_id == unit_id)
    if lease_status:
        query = query.filter(Lease.lease_status == lease_status)
    return paginate(query, Lease, PageParams(page, limit, sort_by, sort_order))


@router.get("/{lease_id}", response_model=LeaseOut)
def get_lease(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lease = db.query(Lease).filter(Lease.id == lease_id, Lease.is_deleted.is_(False)).first()
    if not lease:
        raise NotFoundError("Lease not found")
    return lease


@router.put("/{lease_id}", response_model=LeaseOut)
def update_lease(
    lease_id: int,
    payload: LeaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    lease = db.query(Lease).filter(Lease.id == lease_id, Lease.is_deleted.is_(False)).first()
    if not lease:
        raise NotFoundError("Lease not found")

    data = payload.model_dump(exclude_unset=True)
    new_status = data.pop("lease_status", None)
    for field, value in data.items():
        setattr(lease, field, value)
    db.commit()
    db.refresh(lease)

    if new_status is not None and new_status != lease.lease_status:
        lease = lease_service.update_lease_status(db, lease, new_status, current_user.id)
    else:
        write_audit_log(db, current_user.id, "UPDATE", "Lease", lease.id)
    return lease


@router.put("/{lease_id}/terminate", response_model=LeaseOut)
def terminate_lease(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    return lease_service.terminate_lease(db, lease_id, current_user.id)
