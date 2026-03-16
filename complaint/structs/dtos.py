from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID
class ComplaintCreate(BaseModel):
    booking_id: Optional[str] = None
    category: str
    description: str
    proof_image: Optional[str] = None  
class ComplaintOut(BaseModel):
    id: UUID
    account_id: Optional[UUID]
    registration_id: Optional[UUID] = None
    booking_id: Optional[UUID]
    category: str
    phone: Optional[str]      # Reporter's Phone
    user_name: str            # Reporter's Name
    description: str
    proof_image: Optional[str]
    status: str
    created_at: datetime
    
    # New Helper Fields
    helper_id: Optional[UUID] = None
    helper_name: Optional[str] = "N/A"
    helper_phone: Optional[str] = "N/A"

    class Config:
        from_attributes = True