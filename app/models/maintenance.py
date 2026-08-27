import enum
import datetime

from sqlalchemy import Column, Integer, Float, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class MaintenancePriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    EMERGENCY = "Emergency"


class MaintenanceStatus(str, enum.Enum):
    OPEN = "Open"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class MaintenanceRequest(Base, TimestampMixin):
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=False)
    priority = Column(Enum(MaintenancePriority), nullable=False, default=MaintenancePriority.MEDIUM, index=True)
    assigned_staff_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    status = Column(Enum(MaintenanceStatus), nullable=False, default=MaintenanceStatus.OPEN, index=True)

    tenant = relationship("Tenant")
    unit = relationship("Unit")
    assigned_staff = relationship("User")
    history = relationship(
        "MaintenanceHistory", back_populates="request", cascade="all, delete-orphan"
    )


class MaintenanceHistory(Base):
    """Append-only log of every status/assignment change for a maintenance request."""

    __tablename__ = "maintenance_history"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("maintenance_requests.id"), nullable=False, index=True)
    note = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    request = relationship("MaintenanceRequest", back_populates="history")
