from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ConflictError, BusinessRuleError
from app.models.facility import Facility, FacilityBooking, BookingStatus
from app.models.tenant import Tenant
from app.schemas.facility import FacilityBookingCreate
from app.services.notification_service import notify_booking_confirmation
from app.utils.audit import write_audit_log


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


def book_facility(
    db: Session, facility_id: int, payload: FacilityBookingCreate, actor_id: int | None
) -> FacilityBooking:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise NotFoundError("Facility not found")

    tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id, Tenant.is_deleted.is_(False)).first()
    if not tenant:
        raise NotFoundError("Tenant not found")

    # Business rule: prevent overlapping bookings for the same facility/day.
    same_day_bookings = (
        db.query(FacilityBooking)
        .filter(
            FacilityBooking.facility_id == facility_id,
            FacilityBooking.booking_date == payload.booking_date,
            FacilityBooking.status == BookingStatus.CONFIRMED,
        )
        .all()
    )
    overlapping = [
        b for b in same_day_bookings
        if _overlaps(payload.start_time, payload.end_time, b.start_time, b.end_time)
    ]

    # Business rule: facility capacity cannot be exceeded.
    if len(overlapping) >= facility.capacity:
        raise ConflictError(
            f"Facility '{facility.facility_name}' is at capacity ({facility.capacity}) for this time slot"
        )

    booking = FacilityBooking(
        facility_id=facility_id,
        tenant_id=payload.tenant_id,
        booking_date=payload.booking_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    notify_booking_confirmation(payload.tenant_id, facility.facility_name, str(payload.booking_date))
    write_audit_log(db, actor_id, "CREATE", "FacilityBooking", booking.id)
    return booking


def cancel_booking(db: Session, booking_id: int, actor_id: int | None) -> FacilityBooking:
    booking = db.query(FacilityBooking).filter(FacilityBooking.id == booking_id).first()
    if not booking:
        raise NotFoundError("Booking not found")
    if booking.status == BookingStatus.CANCELLED:
        raise BusinessRuleError("Booking is already cancelled")

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    write_audit_log(db, actor_id, "UPDATE", "FacilityBooking", booking.id, {"action": "cancel"})
    return booking
