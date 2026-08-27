from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.lease import LeaseStatus


class LeaseBase(BaseModel):
    tenant_id: int
    unit_id: int
    start_date: date
    end_date: date
    monthly_rent: float = Field(..., gt=0)
    security_deposit: float = Field(..., gt=0)


class LeaseCreate(LeaseBase):
    lease_status: LeaseStatus = LeaseStatus.DRAFT

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class LeaseUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    monthly_rent: Optional[float] = Field(None, gt=0)
    security_deposit: Optional[float] = Field(None, gt=0)
    lease_status: Optional[LeaseStatus] = None


class LeaseOut(LeaseBase):
    id: int
    lease_status: LeaseStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
