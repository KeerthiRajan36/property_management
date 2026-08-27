from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, model_validator

from app.models.facility import FacilityType, BookingStatus


class FacilityCreate(BaseModel):
    facility_name: str
    facility_type: FacilityType
    capacity: int = 1
    property_id: Optional[int] = None
    description: Optional[str] = None


class FacilityOut(BaseModel):
    id: int
    facility_name: str
    facility_type: FacilityType
    capacity: int
    property_id: Optional[int] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class FacilityBookingCreate(BaseModel):
    tenant_id: int
    booking_date: date
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def check_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class FacilityBookingOut(BaseModel):
    id: int
    facility_id: int
    tenant_id: int
    booking_date: date
    start_time: time
    end_time: time
    status: BookingStatus
    created_at: datetime

    class Config:
        from_attributes = True
