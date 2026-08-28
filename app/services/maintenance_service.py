from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, BusinessRuleError
from app.models.maintenance import MaintenanceRequest, MaintenanceHistory, MaintenanceStatus
from app.models.tenant import Tenant
from app.models.building import Unit
from app.models.user import User, UserRole
from app.schemas.maintenance import MaintenanceCreate
from app.services.notification_service import notify_maintenance_update
from app.routes.websocket import broadcast_sync
from app.utils.audit import write_audit_log


def create_request(db: Session, payload: MaintenanceCreate, actor_id: int | None) -> MaintenanceRequest:
    if not db.query(Tenant).filter(Tenant.id == payload.tenant_id, Tenant.is_deleted.is_(False)).first():
        raise NotFoundError("Tenant not found")
    if not db.query(Unit).filter(Unit.id == payload.unit_id, Unit.is_deleted.is_(False)).first():
        raise NotFoundError("Unit not found")

    request = MaintenanceRequest(**payload.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)

    note = f"Request created with priority {request.priority.value}"
    db.add(MaintenanceHistory(request_id=request.id, note=note))
    db.commit()

    write_audit_log(db, actor_id, "CREATE", "MaintenanceRequest", request.id)
    broadcast_sync(
        {
            "event": "maintenance_created",
            "request_id": request.id,
            "priority": request.priority.value,
            "status": request.status.value,
        }
    )
    return request


def assign_staff(db: Session, request: MaintenanceRequest, staff_id: int, actor_id: int | None) -> MaintenanceRequest:
    staff = db.query(User).filter(User.id == staff_id, User.is_deleted.is_(False)).first()
    if not staff:
        raise NotFoundError("Staff member not found")

    # Business rule: only available maintenance staff can be assigned.
    if staff.role != UserRole.MAINTENANCE_STAFF:
        raise BusinessRuleError("Only users with the Maintenance Staff role can be assigned")
    if not staff.is_active:
        raise BusinessRuleError("Staff member is not active/available")

    request.assigned_staff_id = staff.id
    request.status = MaintenanceStatus.ASSIGNED
    db.add(MaintenanceHistory(request_id=request.id, note=f"Assigned to staff #{staff.id}"))
    db.commit()
    db.refresh(request)

    notify_maintenance_update(request.tenant_id, request.id, request.status.value)
    write_audit_log(db, actor_id, "UPDATE", "MaintenanceRequest", request.id, {"assigned_staff_id": staff.id})
    broadcast_sync(
        {"event": "maintenance_assigned", "request_id": request.id, "assigned_staff_id": staff.id}
    )
    return request


def update_status(
    db: Session,
    request: MaintenanceRequest,
    new_status: MaintenanceStatus,
    actual_cost: float | None,
    note: str | None,
    actor_id: int | None,
) -> MaintenanceRequest:
    request.status = new_status
    if actual_cost is not None:
        request.actual_cost = actual_cost

    history_note = note or f"Status changed to {new_status.value}"
    db.add(MaintenanceHistory(request_id=request.id, note=history_note))
    db.commit()
    db.refresh(request)

    notify_maintenance_update(request.tenant_id, request.id, request.status.value)
    write_audit_log(db, actor_id, "UPDATE", "MaintenanceRequest", request.id, {"status": new_status.value})
    broadcast_sync(
        {"event": "maintenance_status_changed", "request_id": request.id, "status": new_status.value}
    )
    return request
