from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from app.models.visitor import VisitorStatus


class VisitorCreate(BaseModel):
    visitor_name: str
    phone: str
    tenant_id: int
    unit_id: int
    purpose: Optional[str] = None


class VisitorOut(BaseModel):
    id: int
    visitor_name: str
    phone: str
    tenant_id: int
    unit_id: int
    purpose: Optional[str] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    visitor_status: VisitorStatus
    created_at: datetime

    class Config:
        from_attributes = True
