from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.exceptions import NotFoundError, BusinessRuleError, ConflictError
from app.models.building import Unit, UnitStatus
from app.models.lease import Lease, LeaseStatus
from app.models.tenant import Tenant
from app.schemas.lease import LeaseCreate
from app.utils.audit import write_audit_log


def _overlaps(existing: Lease, start, end) -> bool:
    # Two date ranges overlap unless one ends before the other starts.
    return not (end < existing.start_date or start > existing.end_date)


def create_lease(db: Session, payload: LeaseCreate, actor_id: int | None) -> Lease:
    tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id, Tenant.is_deleted.is_(False)).first()
    if not tenant:
        raise NotFoundError("Tenant not found")

    unit = db.query(Unit).filter(Unit.id == payload.unit_id, Unit.is_deleted.is_(False)).first()
    if not unit:
        raise NotFoundError("Unit not found")

    # Business rule: maintenance units cannot be leased.
    if unit.status == UnitStatus.MAINTENANCE:
        raise BusinessRuleError("Unit is under maintenance and cannot be leased")

    # Business rule: occupied units cannot be assigned to another tenant.
    if unit.status == UnitStatus.OCCUPIED and payload.lease_status == LeaseStatus.ACTIVE:
        raise ConflictError("Unit is already occupied by another tenant")

    # Business rule: a unit cannot have overlapping ACTIVE leases.
    active_leases_for_unit = (
        db.query(Lease)
        .filter(
            Lease.unit_id == unit.id,
            Lease.is_deleted.is_(False),
            Lease.lease_status.in_([LeaseStatus.ACTIVE, LeaseStatus.DRAFT]),
        )
        .all()
    )
    for existing in active_leases_for_unit:
        if _overlaps(existing, payload.start_date, payload.end_date):
            raise ConflictError(
                f"Unit already has a lease (#{existing.id}) overlapping this date range"
            )

    lease = Lease(**payload.model_dump())
    db.add(lease)

    # Business rule: unit status automatically becomes Occupied when a lease becomes Active.
    if lease.lease_status == LeaseStatus.ACTIVE:
        unit.status = UnitStatus.OCCUPIED

    db.commit()
    db.refresh(lease)
    write_audit_log(db, actor_id, "CREATE", "Lease", lease.id, {"unit_id": unit.id, "tenant_id": tenant.id})
    return lease


def update_lease_status(db: Session, lease: Lease, new_status: LeaseStatus, actor_id: int | None) -> Lease:
    unit = db.query(Unit).filter(Unit.id == lease.unit_id).first()

    if new_status == LeaseStatus.ACTIVE and lease.lease_status != LeaseStatus.ACTIVE:
        if unit and unit.status == UnitStatus.OCCUPIED:
            raise ConflictError("Unit is already occupied by another active lease")
        if unit:
            unit.status = UnitStatus.OCCUPIED

    if new_status in (LeaseStatus.TERMINATED, LeaseStatus.EXPIRED) and unit and unit.status == UnitStatus.OCCUPIED:
        unit.status = UnitStatus.AVAILABLE

    lease.lease_status = new_status
    db.commit()
    db.refresh(lease)
    write_audit_log(db, actor_id, "UPDATE", "Lease", lease.id, {"new_status": new_status.value})
    return lease


def terminate_lease(db: Session, lease_id: int, actor_id: int | None) -> Lease:
    lease = db.query(Lease).filter(Lease.id == lease_id, Lease.is_deleted.is_(False)).first()
    if not lease:
        raise NotFoundError("Lease not found")
    if lease.lease_status == LeaseStatus.TERMINATED:
        raise ConflictError("Lease is already terminated")
    return update_lease_status(db, lease, LeaseStatus.TERMINATED, actor_id)
