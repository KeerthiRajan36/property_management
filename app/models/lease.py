import enum

from sqlalchemy import Column, Integer, Float, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class LeaseStatus(str, enum.Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    EXPIRED = "Expired"
    TERMINATED = "Terminated"


class Lease(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    monthly_rent = Column(Float, nullable=False)
    security_deposit = Column(Float, nullable=False)
    lease_status = Column(Enum(LeaseStatus), nullable=False, default=LeaseStatus.DRAFT, index=True)

    tenant = relationship("Tenant", back_populates="leases")
    unit = relationship("Unit", back_populates="leases")
    invoices = relationship("RentInvoice", back_populates="lease")
