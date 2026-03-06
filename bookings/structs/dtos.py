from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

class ApplyToHelperSchema(BaseModel):
    helper_reg_id: UUID
    service_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    address: str
    notes: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "helper_reg_id": "550e8400-e29b-41d4-a716-446655440000",
                "service_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "scheduled_start": "2026-03-10T09:00:00Z",
                "scheduled_end": "2026-03-10T12:00:00Z",
                "address": "123 Main St, New Town",
                "notes": "Please bring your own cleaning supplies."
            }
        }