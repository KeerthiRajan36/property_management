from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from app.models.parking import ParkingVehicleType, ParkingStatus


class ParkingCreate(BaseModel):
    property_id: int
    parking_number: str


class ParkingAssign(BaseModel):
    tenant_id: int
    vehicle_number: str
    vehicle_type: ParkingVehicleType


class ParkingOut(BaseModel):
    id: int
    property_id: int
    parking_number: str
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[ParkingVehicleType] = None
    tenant_id: Optional[int] = None
    status: ParkingStatus
    created_at: datetime

    class Config:
        from_attributes = True
