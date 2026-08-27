import enum
import datetime

from sqlalchemy import Column, Integer, String, Time, Date, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class FacilityType(str, enum.Enum):
    GYM = "Gym"
    SWIMMING_POOL = "Swimming Pool"
    CONFERENCE_ROOM = "Conference Room"
    CLUB_HOUSE = "Club House"
    SPORTS_AREA = "Sports Area"


class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    facility_name = Column(String(150), nullable=False)
    facility_type = Column(Enum(FacilityType), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True, index=True)
    capacity = Column(Integer, nullable=False, default=1)
    description = Column(String(500), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)  # 1/0 flag, sqlite-friendly

    property = relationship("Property")
    bookings = relationship("FacilityBooking", back_populates="facility")


class BookingStatus(str, enum.Enum):
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"


class FacilityBooking(Base):
    __tablename__ = "facility_bookings"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    booking_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.CONFIRMED, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    facility = relationship("Facility", back_populates="bookings")
    tenant = relationship("Tenant")
