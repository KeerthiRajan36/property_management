from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.maintenance import MaintenancePriority, MaintenanceStatus


class MaintenanceCreate(BaseModel):
    tenant_id: int
    unit_id: int
    category: str
    description: str
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    estimated_cost: Optional[float] = None


class MaintenanceAssign(BaseModel):
    assigned_staff_id: int


class MaintenanceStatusUpdate(BaseModel):
    status: MaintenanceStatus
    actual_cost: Optional[float] = None
    note: Optional[str] = None


class MaintenanceOut(BaseModel):
    id: int
    tenant_id: int
    unit_id: int
    category: str
    description: str
    priority: MaintenancePriority
    assigned_staff_id: Optional[int] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    status: MaintenanceStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaintenanceHistoryOut(BaseModel):
    id: int
    note: str
    created_at: datetime

    class Config:
        from_attributes = True
