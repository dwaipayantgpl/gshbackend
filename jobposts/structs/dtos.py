# jobs/structs/dtos.py
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


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
