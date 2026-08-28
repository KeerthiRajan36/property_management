import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.audit import Notification

logger = logging.getLogger("notifications")


def _dispatch(message: str, user_id: int | None, tenant_id: int | None):
    # Stub for real email/SMS/push delivery.
    logger.info("NOTIFICATION -> user_id=%s tenant_id=%s : %s", user_id, tenant_id, message)


def send_notification(
    notif_type: str,
    message: str,
    user_id: int | None = None,
    tenant_id: int | None = None,
):

    db: Session = SessionLocal()
    try:
        record = Notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=notif_type,
            message=message,
        )
        db.add(record)
        db.commit()
        _dispatch(message, user_id, tenant_id)
    finally:
        db.close()



def notify_rent_due(tenant_id: int, invoice_id: int, amount: float, due_date: str):
    send_notification(
        "RENT_DUE",
        f"Rent invoice #{invoice_id} of {amount} is due on {due_date}.",
        tenant_id=tenant_id,
    )


def notify_rent_overdue(tenant_id: int, invoice_id: int, amount: float):
    send_notification(
        "RENT_OVERDUE",
        f"Rent invoice #{invoice_id} of {amount} is now overdue. Please pay immediately.",
        tenant_id=tenant_id,
    )


def notify_maintenance_update(tenant_id: int, request_id: int, status: str):
    send_notification(
        "MAINTENANCE_UPDATE",
        f"Your maintenance request #{request_id} status changed to '{status}'.",
        tenant_id=tenant_id,
    )


def notify_visitor_approval(tenant_id: int, visitor_name: str):
    send_notification(
        "VISITOR_APPROVAL",
        f"Visitor '{visitor_name}' is expected and awaiting your approval / check-in.",
        tenant_id=tenant_id,
    )


def notify_booking_confirmation(tenant_id: int, facility_name: str, booking_date: str):
    send_notification(
        "BOOKING_CONFIRMATION",
        f"Your booking for '{facility_name}' on {booking_date} is confirmed.",
        tenant_id=tenant_id,
    )


def notify_lease_expiry(tenant_id: int, lease_id: int, end_date: str):
    send_notification(
        "LEASE_EXPIRY",
        f"Your lease #{lease_id} is expiring on {end_date}. Please contact your property manager.",
        tenant_id=tenant_id,
    )
