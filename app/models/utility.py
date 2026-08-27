import enum
import datetime

from sqlalchemy import Column, Integer, Float, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class UtilityType(str, enum.Enum):
    ELECTRICITY = "Electricity"
    WATER = "Water"
    GAS = "Gas"
    INTERNET = "Internet"


class UtilityReading(Base):
    __tablename__ = "utility_readings"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    utility_type = Column(Enum(UtilityType), nullable=False, index=True)
    previous_reading = Column(Float, nullable=False)
    current_reading = Column(Float, nullable=False)
    units_consumed = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    billing_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    unit = relationship("Unit")
    invoice = relationship("UtilityInvoice", back_populates="reading", uselist=False)


class UtilityInvoiceStatus(str, enum.Enum):
    PENDING = "Pending"
    PAID = "Paid"


class UtilityInvoice(Base):
    __tablename__ = "utility_invoices"

    id = Column(Integer, primary_key=True, index=True)
    reading_id = Column(Integer, ForeignKey("utility_readings.id"), nullable=False, unique=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    utility_type = Column(Enum(UtilityType), nullable=False)
    billing_month = Column(String(7), nullable=False, index=True)
    units_consumed = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(UtilityInvoiceStatus), nullable=False, default=UtilityInvoiceStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    reading = relationship("UtilityReading", back_populates="invoice")
    unit = relationship("Unit")
