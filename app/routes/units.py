from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError, ConflictError
from app.models.building import Unit, UnitType, UnitStatus
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.building import UnitCreate, UnitUpdate, UnitOut
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/units", tags=["Units"])


def get_repo(db: Session = Depends(get_db)) -> BaseRepository:
    return BaseRepository(db, Unit)


@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    # Business rule: unit number must be unique within a building
    dupe = (
        db.query(Unit)
        .filter(
            Unit.building_id == payload.building_id,
            Unit.unit_number == payload.unit_number,
            Unit.is_deleted.is_(False),
        )
        .first()
    )
    if dupe:
        raise ConflictError("Unit number already exists in this building")

    unit = repo.create(payload.model_dump())
    write_audit_log(db, current_user.id, "CREATE", "Unit", unit.id)
    return unit


@router.get("", response_model=PaginatedResponse[UnitOut])
def list_units(
    building_id: Optional[int] = None,
    unit_type: Optional[UnitType] = None,
    status_: Optional[UnitStatus] = None,
    min_rent: Optional[float] = None,
    max_rent: Optional[float] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    query = repo.query()
    if building_id:
        query = query.filter(Unit.building_id == building_id)
    if unit_type:
        query = query.filter(Unit.unit_type == unit_type)
    if status_:
        query = query.filter(Unit.status == status_)
    if min_rent is not None:
        query = query.filter(Unit.monthly_rent >= min_rent)
    if max_rent is not None:
        query = query.filter(Unit.monthly_rent <= max_rent)
    return paginate(query, Unit, PageParams(page, limit, sort_by, sort_order))


@router.get("/{unit_id}", response_model=UnitOut)
def get_unit(
    unit_id: int,
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    unit = repo.get(unit_id)
    if not unit:
        raise NotFoundError("Unit not found")
    return unit


@router.put("/{unit_id}", response_model=UnitOut)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    unit = repo.get(unit_id)
    if not unit:
        raise NotFoundError("Unit not found")

    data = payload.model_dump(exclude_unset=True)

    if data.get("status") == UnitStatus.AVAILABLE and unit.status == UnitStatus.OCCUPIED:
        from app.models.lease import Lease, LeaseStatus

        active_lease = (
            db.query(Lease)
            .filter(Lease.unit_id == unit.id, Lease.lease_status == LeaseStatus.ACTIVE)
            .first()
        )
        if active_lease:
            raise ConflictError(
                "Unit has an active lease; terminate the lease before freeing the unit"
            )

    unit = repo.update(unit, data)
    write_audit_log(db, current_user.id, "UPDATE", "Unit", unit.id)
    return unit
