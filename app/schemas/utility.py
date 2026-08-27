from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.utility import UtilityType, UtilityInvoiceStatus


class UtilityReadingCreate(BaseModel):
    unit_id: int
    utility_type: UtilityType
    previous_reading: float = Field(..., ge=0)
    current_reading: float = Field(..., ge=0)
    rate: float = Field(..., gt=0)
    billing_month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")

    @model_validator(mode="after")
    def check_readings(self):
        if self.current_reading < self.previous_reading:
            raise ValueError("current_reading cannot be lower than previous_reading")
        return self


class UtilityReadingOut(BaseModel):
    id: int
    unit_id: int
    utility_type: UtilityType
    previous_reading: float
    current_reading: float
    units_consumed: float
    rate: float
    billing_month: str
    created_at: datetime

    class Config:
        from_attributes = True


class UtilityInvoiceCreate(BaseModel):
    reading_id: int


class UtilityInvoiceOut(BaseModel):
    id: int
    reading_id: int
    unit_id: int
    utility_type: UtilityType
    billing_month: str
    units_consumed: float
    rate: float
    total_amount: float
    status: UtilityInvoiceStatus
    created_at: datetime

    class Config:
        from_attributes = True
