from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.exceptions import NotFoundError
from app.models.facility import Facility, FacilityBooking, FacilityType, BookingStatus
from app.models.user import User, UserRole
from app.schemas.facility import (
    FacilityCreate,
    FacilityOut,
    FacilityBookingCreate,
    FacilityBookingOut,
)
from app.services import facility_service
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/facilities", tags=["Facilities"])

require_facility_admin = require_roles(UserRole.SUPER_ADMIN, UserRole.FACILITY_MANAGER, UserRole.PROPERTY_MANAGER)


@router.post("", response_model=FacilityOut, status_code=status.HTTP_201_CREATED)
def create_facility(
    payload: FacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_facility_admin),
):
    facility = Facility(**payload.model_dump())
    db.add(facility)
    db.commit()
    db.refresh(facility)
    write_audit_log(db, current_user.id, "CREATE", "Facility", facility.id)
    return facility


@router.get("", response_model=PaginatedResponse[FacilityOut])
def list_facilities(
    facility_type: Optional[FacilityType] = None,
    property_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Facility)
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type)
    if property_id:
        query = query.filter(Facility.property_id == property_id)
    return paginate(query, Facility, PageParams(page, limit, sort_by, sort_order))


@router.post("/{facility_id}/book", response_model=FacilityBookingOut, status_code=status.HTTP_201_CREATED)
def book_facility(
    facility_id: int,
    payload: FacilityBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return facility_service.book_facility(db, facility_id, payload, current_user.id)


@router.get("/bookings", response_model=PaginatedResponse[FacilityBookingOut])
def list_bookings(
    facility_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    booking_date: Optional[date] = None,
    status_: Optional[BookingStatus] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(FacilityBooking)
    if facility_id:
        query = query.filter(FacilityBooking.facility_id == facility_id)
    if tenant_id:
        query = query.filter(FacilityBooking.tenant_id == tenant_id)
    if booking_date:
        query = query.filter(FacilityBooking.booking_date == booking_date)
    if status_:
        query = query.filter(FacilityBooking.status == status_)
    return paginate(query, FacilityBooking, PageParams(page, limit, sort_by, sort_order))


@router.put("/bookings/{booking_id}/cancel", response_model=FacilityBookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return facility_service.cancel_booking(db, booking_id, current_user.id)
