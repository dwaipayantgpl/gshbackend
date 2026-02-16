# jobs/structs/dtos.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class JobRequestCreateIn(BaseModel):
    headline: str = Field(..., examples=["Need a Home Nurse"])
    description: str
    city: str
    area: str
    contact_phone: Optional[str] = None
    job_type: str  # part_time, full_time, etc.
    service_ids: List[str]  # IDs from the Service table

class JobRequestOut(BaseModel):
    id: uuid.UUID
    seeker_id: uuid.UUID
    headline: str
    description: str
    city: str
    area: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True