from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.building import UnitType, UnitStatus


class BuildingBase(BaseModel):
    property_id: int
    building_name: str = Field(..., min_length=1, max_length=150)
    number_of_floors: int = Field(..., ge=1)
    total_units: int = Field(0, ge=0)


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    building_name: Optional[str] = None
    number_of_floors: Optional[int] = Field(None, ge=1)
    total_units: Optional[int] = Field(None, ge=0)


class BuildingOut(BuildingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UnitBase(BaseModel):
    building_id: int
    unit_number: str = Field(..., min_length=1, max_length=30)
    floor_number: int = Field(..., ge=0)
    unit_type: UnitType
    area: float = Field(..., gt=0)
    monthly_rent: float = Field(..., gt=0)
    status: UnitStatus = UnitStatus.AVAILABLE


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    unit_number: Optional[str] = None
    floor_number: Optional[int] = Field(None, ge=0)
    unit_type: Optional[UnitType] = None
    area: Optional[float] = Field(None, gt=0)
    monthly_rent: Optional[float] = Field(None, gt=0)
    status: Optional[UnitStatus] = None


class UnitOut(UnitBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
