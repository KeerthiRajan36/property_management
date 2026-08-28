from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError, ConflictError, BusinessRuleError
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.parking import ParkingSlot, ParkingStatus
from app.models.user import User
from app.schemas.parking import ParkingCreate, ParkingAssign, ParkingOut
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/parking", tags=["Parking"])


@router.post("", response_model=ParkingOut, status_code=status.HTTP_201_CREATED)
def create_parking_slot(
    payload: ParkingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    if not db.query(Property).filter(Property.id == payload.property_id, Property.is_deleted.is_(False)).first():
        raise NotFoundError("Property not found")

    slot = ParkingSlot(property_id=payload.property_id, parking_number=payload.parking_number)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    write_audit_log(db, current_user.id, "CREATE", "ParkingSlot", slot.id)
    return slot


@router.get("", response_model=PaginatedResponse[ParkingOut])
def list_parking_slots(
    property_id: Optional[int] = None,
    status_: Optional[ParkingStatus] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ParkingSlot)
    if property_id:
        query = query.filter(ParkingSlot.property_id == property_id)
    if status_:
        query = query.filter(ParkingSlot.status == status_)
    return paginate(query, ParkingSlot, PageParams(page, limit, sort_by, sort_order))


@router.post("/{parking_id}/assign", response_model=ParkingOut)
def assign_parking(
    parking_id: int,
    payload: ParkingAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    slot = db.query(ParkingSlot).filter(ParkingSlot.id == parking_id).first()
    if not slot:
        raise NotFoundError("Parking slot not found")
    if not db.query(Tenant).filter(Tenant.id == payload.tenant_id, Tenant.is_deleted.is_(False)).first():
        raise NotFoundError("Tenant not found")

    # Business rule: one slot cannot be assigned to multiple active vehicles.
    if slot.status == ParkingStatus.ASSIGNED:
        raise ConflictError("Parking slot is already assigned to another vehicle")
    if slot.status == ParkingStatus.BLOCKED:
        raise BusinessRuleError("Parking slot is blocked and cannot be assigned")

    # Business rule: vehicle number must be unique across all slots.
    dupe = (
        db.query(ParkingSlot)
        .filter(ParkingSlot.vehicle_number == payload.vehicle_number, ParkingSlot.status == ParkingStatus.ASSIGNED)
        .first()
    )
    if dupe:
        raise ConflictError("This vehicle number is already assigned to another parking slot")

    slot.tenant_id = payload.tenant_id
    slot.vehicle_number = payload.vehicle_number
    slot.vehicle_type = payload.vehicle_type
    slot.status = ParkingStatus.ASSIGNED
    db.commit()
    db.refresh(slot)
    write_audit_log(db, current_user.id, "UPDATE", "ParkingSlot", slot.id, {"action": "assign"})
    return slot


@router.put("/{parking_id}/release", response_model=ParkingOut)
def release_parking(
    parking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    slot = db.query(ParkingSlot).filter(ParkingSlot.id == parking_id).first()
    if not slot:
        raise NotFoundError("Parking slot not found")
    slot.tenant_id = None
    slot.vehicle_number = None
    slot.vehicle_type = None
    slot.status = ParkingStatus.AVAILABLE
    db.commit()
    db.refresh(slot)
    write_audit_log(db, current_user.id, "UPDATE", "ParkingSlot", slot.id, {"action": "release"})
    return slot
