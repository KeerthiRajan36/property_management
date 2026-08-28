from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.building import Building, Unit, UnitStatus
from app.models.tenant import Tenant
from app.models.lease import Lease, LeaseStatus
from app.models.rent import RentInvoice, InvoiceStatus
from app.models.maintenance import MaintenanceRequest
from app.models.utility import UtilityInvoice
from app.models.parking import ParkingSlot, ParkingStatus


def get_summary(db: Session) -> dict:
    total_properties = db.query(func.count(Property.id)).filter(Property.is_deleted.is_(False)).scalar() or 0
    total_buildings = db.query(func.count(Building.id)).filter(Building.is_deleted.is_(False)).scalar() or 0
    total_units = db.query(func.count(Unit.id)).filter(Unit.is_deleted.is_(False)).scalar() or 0
    occupied_units = (
        db.query(func.count(Unit.id))
        .filter(Unit.is_deleted.is_(False), Unit.status == UnitStatus.OCCUPIED)
        .scalar()
        or 0
    )
    available_units = (
        db.query(func.count(Unit.id))
        .filter(Unit.is_deleted.is_(False), Unit.status == UnitStatus.AVAILABLE)
        .scalar()
        or 0
    )
    total_tenants = db.query(func.count(Tenant.id)).filter(Tenant.is_deleted.is_(False)).scalar() or 0
    active_leases = (
        db.query(func.count(Lease.id))
        .filter(Lease.is_deleted.is_(False), Lease.lease_status == LeaseStatus.ACTIVE)
        .scalar()
        or 0
    )

    monthly_rent_collection = (
        db.query(func.coalesce(func.sum(RentInvoice.total_amount), 0.0))
        .filter(RentInvoice.status == InvoiceStatus.PAID)
        .scalar()
        or 0.0
    )
    pending_rent = (
        db.query(func.coalesce(func.sum(RentInvoice.total_amount), 0.0))
        .filter(RentInvoice.status == InvoiceStatus.PENDING)
        .scalar()
        or 0.0
    )
    overdue_rent = (
        db.query(func.coalesce(func.sum(RentInvoice.total_amount), 0.0))
        .filter(RentInvoice.status == InvoiceStatus.OVERDUE)
        .scalar()
        or 0.0
    )
    maintenance_expenses = (
        db.query(func.coalesce(func.sum(MaintenanceRequest.actual_cost), 0.0)).scalar() or 0.0
    )
    utility_revenue = (
        db.query(func.coalesce(func.sum(UtilityInvoice.total_amount), 0.0)).scalar() or 0.0
    )

    total_parking = db.query(func.count(ParkingSlot.id)).scalar() or 0
    assigned_parking = (
        db.query(func.count(ParkingSlot.id)).filter(ParkingSlot.status == ParkingStatus.ASSIGNED).scalar() or 0
    )
    parking_occupancy = (assigned_parking / total_parking * 100.0) if total_parking else 0.0

    return {
        "total_properties": total_properties,
        "total_buildings": total_buildings,
        "total_units": total_units,
        "occupied_units": occupied_units,
        "available_units": available_units,
        "total_tenants": total_tenants,
        "active_leases": active_leases,
        "monthly_rent_collection": monthly_rent_collection,
        "pending_rent": pending_rent,
        "overdue_rent": overdue_rent,
        "maintenance_expenses": maintenance_expenses,
        "utility_revenue": utility_revenue,
        "parking_occupancy": round(parking_occupancy, 2),
    }


def report_monthly_rent_collection(db: Session):
    rows = (
        db.query(RentInvoice.billing_month, func.sum(RentInvoice.total_amount))
        .filter(RentInvoice.status == InvoiceStatus.PAID)
        .group_by(RentInvoice.billing_month)
        .order_by(RentInvoice.billing_month)
        .all()
    )
    return [{"billing_month": r[0], "total_collected": r[1] or 0.0} for r in rows]


def report_property_wise_revenue(db: Session):
    rows = (
        db.query(Property.property_name, func.sum(RentInvoice.total_amount))
        .join(Lease, Lease.id == RentInvoice.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Building, Building.id == Unit.building_id)
        .join(Property, Property.id == Building.property_id)
        .filter(RentInvoice.status == InvoiceStatus.PAID)
        .group_by(Property.property_name)
        .all()
    )
    return [{"property_name": r[0], "revenue": r[1] or 0.0} for r in rows]


def report_unit_occupancy(db: Session):
    rows = (
        db.query(Unit.status, func.count(Unit.id))
        .filter(Unit.is_deleted.is_(False))
        .group_by(Unit.status)
        .all()
    )
    return [{"status": r[0].value if hasattr(r[0], "value") else r[0], "count": r[1]} for r in rows]


def report_maintenance_expense(db: Session):
    rows = (
        db.query(MaintenanceRequest.category, func.sum(MaintenanceRequest.actual_cost))
        .group_by(MaintenanceRequest.category)
        .all()
    )
    return [{"category": r[0], "total_expense": r[1] or 0.0} for r in rows]


def report_utility_consumption(db: Session):
    rows = (
        db.query(UtilityInvoice.utility_type, func.sum(UtilityInvoice.units_consumed), func.sum(UtilityInvoice.total_amount))
        .group_by(UtilityInvoice.utility_type)
        .all()
    )
    return [
        {
            "utility_type": r[0].value if hasattr(r[0], "value") else r[0],
            "total_units_consumed": r[1] or 0.0,
            "total_amount": r[2] or 0.0,
        }
        for r in rows
    ]


def report_tenant_payment_history(db: Session, tenant_id: int):
    from app.models.rent import Payment

    rows = (
        db.query(Payment)
        .join(RentInvoice, RentInvoice.id == Payment.invoice_id)
        .join(Lease, Lease.id == RentInvoice.lease_id)
        .filter(Lease.tenant_id == tenant_id)
        .order_by(Payment.payment_date.desc())
        .all()
    )
    return rows


def report_lease_expiry(db: Session, days_ahead: int = 30):
    import datetime

    cutoff = datetime.date.today() + datetime.timedelta(days=days_ahead)
    rows = (
        db.query(Lease)
        .filter(
            Lease.is_deleted.is_(False),
            Lease.lease_status == LeaseStatus.ACTIVE,
            Lease.end_date <= cutoff,
        )
        .order_by(Lease.end_date.asc())
        .all()
    )
    return rows
