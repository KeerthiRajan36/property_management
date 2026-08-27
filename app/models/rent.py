import enum
import datetime

from sqlalchemy import Column, Integer, Float, Date, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class InvoiceStatus(str, enum.Enum):
    PENDING = "Pending"
    PAID = "Paid"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"


class RentInvoice(Base, TimestampMixin):
    __tablename__ = "rent_invoices"
    __table_args__ = (
        UniqueConstraint("lease_id", "billing_month", name="uq_invoice_per_lease_per_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=False, index=True)
    billing_month = Column(String(7), nullable=False, index=True)  # format YYYY-MM
    rent_amount = Column(Float, nullable=False)
    late_fee = Column(Float, nullable=False, default=0.0)
    discount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.PENDING, index=True)

    lease = relationship("Lease", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("rent_invoices.id"), nullable=False, index=True)
    amount_paid = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=True)
    remarks = Column(String(255), nullable=True)
    payment_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    invoice = relationship("RentInvoice", back_populates="payments")
