from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.property import PropertyType, PropertyStatus


class PropertyBase(BaseModel):
    property_name: str = Field(..., min_length=2, max_length=150)
    property_type: PropertyType
    address: str
    city: str
    state: str
    total_area: float = Field(..., gt=0)
    total_units: int = Field(0, ge=0)
    status: PropertyStatus = PropertyStatus.ACTIVE


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    property_name: Optional[str] = None
    property_type: Optional[PropertyType] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    total_area: Optional[float] = Field(None, gt=0)
    total_units: Optional[int] = Field(None, ge=0)
    status: Optional[PropertyStatus] = None


class PropertyOut(PropertyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
