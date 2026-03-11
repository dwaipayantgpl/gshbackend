from pydantic import BaseModel, Field
from datetime import date, datetime
from uuid import UUID
from typing import Optional

class BookingSummaryOut(BaseModel):
    booking_id: UUID
    helper_name: str
    service_name: str
    booking_date: date
    time_slot: str
    address: str
    total_price: float
    status: str

class DirectBookingCreate(BaseModel):
    helper_id: UUID
    service_id: UUID
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    address: str
    city: str
    area: str
    pin_code: str
    booking_date: date
    time_slot: str  # Morning, Afternoon, Evening
    work_details: dict  # JSON for rooms, instructions, etc.
    duration: Optional[str] = None
    preferences: Optional[dict] = None
    payment_method: str
    total_price: Optional[float] = None

class BookingUpdateSchema(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    pin_code: Optional[str] = None
    booking_date: Optional[date] = None
    time_slot: Optional[str] = None
    work_details: Optional[dict] = None
    duration: Optional[str] = None
    total_price: Optional[float] = None