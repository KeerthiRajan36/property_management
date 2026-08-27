from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.rent import InvoiceStatus


class InvoiceGenerateRequest(BaseModel):
    lease_id: int
    billing_month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")
    late_fee: float = Field(0.0, ge=0)
    discount: float = Field(0.0, ge=0)
    due_date: date


class InvoiceOut(BaseModel):
    id: int
    lease_id: int
    billing_month: str
    rent_amount: float
    late_fee: float
    discount: float
    total_amount: float
    due_date: date
    status: InvoiceStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    amount_paid: float = Field(..., gt=0)
    payment_method: Optional[str] = None
    remarks: Optional[str] = None


class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    amount_paid: float
    payment_method: Optional[str] = None
    remarks: Optional[str] = None
    payment_date: datetime

    class Config:
        from_attributes = True
