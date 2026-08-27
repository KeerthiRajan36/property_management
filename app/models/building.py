import enum

from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Building(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    building_name = Column(String(150), nullable=False)
    number_of_floors = Column(Integer, nullable=False)
    total_units = Column(Integer, nullable=False, default=0)

    property = relationship("Property", back_populates="buildings")
    units = relationship("Unit", back_populates="building")


class UnitType(str, enum.Enum):
    STUDIO = "Studio"
    ONE_BHK = "1BHK"
    TWO_BHK = "2BHK"
    THREE_BHK = "3BHK"
    OFFICE = "Office"
    SHOP = "Shop"
    WAREHOUSE_UNIT = "WarehouseUnit"


class UnitStatus(str, enum.Enum):
    AVAILABLE = "Available"
    OCCUPIED = "Occupied"
    RESERVED = "Reserved"
    MAINTENANCE = "Maintenance"


class Unit(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("building_id", "unit_number", name="uq_unit_number_per_building"),
    )

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False, index=True)
    unit_number = Column(String(30), nullable=False, index=True)
    floor_number = Column(Integer, nullable=False)
    unit_type = Column(Enum(UnitType), nullable=False)
    area = Column(Float, nullable=False)
    monthly_rent = Column(Float, nullable=False)
    status = Column(Enum(UnitStatus), nullable=False, default=UnitStatus.AVAILABLE, index=True)

    building = relationship("Building", back_populates="units")
    leases = relationship("Lease", back_populates="unit")
