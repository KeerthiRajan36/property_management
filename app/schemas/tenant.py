from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TenantBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str
    identification_number: str
    emergency_contact: Optional[str] = None
    address: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None


class TenantOut(TenantBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
