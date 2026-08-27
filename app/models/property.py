import enum

from sqlalchemy import Column, Integer, String, Float, Enum
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class PropertyType(str, enum.Enum):
    APARTMENT = "Apartment"
    VILLA = "Villa"
    COMMERCIAL = "Commercial"
    OFFICE = "Office"
    WAREHOUSE = "Warehouse"


class PropertyStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    UNDER_MAINTENANCE = "UnderMaintenance"


class Property(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_name = Column(String(150), nullable=False, index=True)
    property_type = Column(Enum(PropertyType), nullable=False, index=True)
    address = Column(String(300), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    total_area = Column(Float, nullable=False)
    total_units = Column(Integer, nullable=False, default=0)
    status = Column(Enum(PropertyStatus), nullable=False, default=PropertyStatus.ACTIVE, index=True)

    buildings = relationship("Building", back_populates="property")
