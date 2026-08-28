from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_staff
from app.exceptions import NotFoundError
from app.models.maintenance import MaintenanceRequest, MaintenancePriority, MaintenanceStatus
from app.models.user import User
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceAssign,
    MaintenanceStatusUpdate,
    MaintenanceOut,
    MaintenanceHistoryOut,
)
from app.services import maintenance_service
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


@router.post("/requests", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return maintenance_service.create_request(db, payload, current_user.id)


@router.get("/requests", response_model=PaginatedResponse[MaintenanceOut])
def list_requests(
    priority: Optional[MaintenancePriority] = None,
    status_: Optional[MaintenanceStatus] = None,
    assigned_staff_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(MaintenanceRequest)
    if priority:
        query = query.filter(MaintenanceRequest.priority == priority)
    if status_:
        query = query.filter(MaintenanceRequest.status == status_)
    if assigned_staff_id:
        query = query.filter(MaintenanceRequest.assigned_staff_id == assigned_staff_id)

    # Business rule: emergency requests surface first by default.
    if sort_by == "id" and sort_order == "asc":
        from sqlalchemy import case

        priority_rank = case(
            (MaintenanceRequest.priority == MaintenancePriority.EMERGENCY, 0),
            (MaintenanceRequest.priority == MaintenancePriority.HIGH, 1),
            (MaintenanceRequest.priority == MaintenancePriority.MEDIUM, 2),
            else_=3,
        )
        query = query.order_by(priority_rank, MaintenanceRequest.created_at.asc())
        total = query.count()
        items = query.offset((page - 1) * limit).limit(limit).all()
        pages = (total + limit - 1) // limit if limit else 1
        return {"total": total, "page": page, "limit": limit, "pages": pages, "items": items}

    return paginate(query, MaintenanceRequest, PageParams(page, limit, sort_by, sort_order))


@router.get("/requests/{request_id}", response_model=MaintenanceOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not request:
        raise NotFoundError("Maintenance request not found")
    return request


@router.get("/requests/{request_id}/history", response_model=list[MaintenanceHistoryOut])
def get_request_history(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.maintenance import MaintenanceHistory

    if not db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first():
        raise NotFoundError("Maintenance request not found")
    return (
        db.query(MaintenanceHistory)
        .filter(MaintenanceHistory.request_id == request_id)
        .order_by(MaintenanceHistory.created_at.asc())
        .all()
    )


@router.put("/requests/{request_id}/assign", response_model=MaintenanceOut)
def assign_request(
    request_id: int,
    payload: MaintenanceAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    request = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not request:
        raise NotFoundError("Maintenance request not found")
    return maintenance_service.assign_staff(db, request, payload.assigned_staff_id, current_user.id)


@router.put("/requests/{request_id}/status", response_model=MaintenanceOut)
def update_request_status(
    request_id: int,
    payload: MaintenanceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    request = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not request:
        raise NotFoundError("Maintenance request not found")
    return maintenance_service.update_status(
        db, request, payload.status, payload.actual_cost, payload.note, current_user.id
    )
