from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError, ConflictError
from app.models.tenant import Tenant
from app.models.lease import Lease
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.building import UnitOut
from app.schemas.lease import LeaseOut
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantOut
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def get_repo(db: Session = Depends(get_db)) -> BaseRepository:
    return BaseRepository(db, Tenant)


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    if db.query(Tenant).filter(Tenant.email == payload.email).first():
        raise ConflictError("A tenant with this email already exists")
    if db.query(Tenant).filter(Tenant.identification_number == payload.identification_number).first():
        raise ConflictError("A tenant with this identification number already exists")

    tenant = repo.create(payload.model_dump())
    write_audit_log(db, current_user.id, "CREATE", "Tenant", tenant.id)
    return tenant


@router.get("", response_model=PaginatedResponse[TenantOut])
def list_tenants(
    name: Optional[str] = None,
    email: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    query = repo.query()
    if name:
        query = query.filter(Tenant.full_name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Tenant.email.ilike(f"%{email}%"))
    return paginate(query, Tenant, PageParams(page, limit, sort_by, sort_order))


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    tenant = repo.get(tenant_id)
    if not tenant:
        raise NotFoundError("Tenant not found")
    return tenant


@router.get("/{tenant_id}/rental-history", response_model=list[LeaseOut])
def tenant_rental_history(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    """Full lease history for a tenant, across every unit they've occupied."""
    tenant = repo.get(tenant_id)
    if not tenant:
        raise NotFoundError("Tenant not found")
    return (
        db.query(Lease)
        .filter(Lease.tenant_id == tenant_id, Lease.is_deleted.is_(False))
        .order_by(Lease.start_date.desc())
        .all()
    )


@router.put("/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    tenant = repo.get(tenant_id)
    if not tenant:
        raise NotFoundError("Tenant not found")
    tenant = repo.update(tenant, payload.model_dump(exclude_unset=True))
    write_audit_log(db, current_user.id, "UPDATE", "Tenant", tenant.id)
    return tenant
