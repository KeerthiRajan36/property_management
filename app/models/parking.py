import enum

from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class ParkingVehicleType(str, enum.Enum):
    CAR = "Car"
    BIKE = "Bike"
    SUV = "SUV"
    OTHER = "Other"


class ParkingStatus(str, enum.Enum):
    AVAILABLE = "Available"
    ASSIGNED = "Assigned"
    BLOCKED = "Blocked"


class ParkingSlot(Base, TimestampMixin):
    __tablename__ = "parking_slots"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    parking_number = Column(String(30), nullable=False, index=True)
    vehicle_number = Column(String(30), nullable=True, unique=True, index=True)
    vehicle_type = Column(Enum(ParkingVehicleType), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    status = Column(Enum(ParkingStatus), nullable=False, default=ParkingStatus.AVAILABLE, index=True)

    property = relationship("Property")
    tenant = relationship("Tenant")
