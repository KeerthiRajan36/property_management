import enum
import datetime

from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class VisitorStatus(str, enum.Enum):
    EXPECTED = "Expected"
    CHECKED_IN = "Checked In"
    CHECKED_OUT = "Checked Out"
    CANCELLED = "Cancelled"


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)
    visitor_name = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    purpose = Column(String(255), nullable=True)
    entry_time = Column(DateTime, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    visitor_status = Column(Enum(VisitorStatus), nullable=False, default=VisitorStatus.EXPECTED, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    unit = relationship("Unit")
