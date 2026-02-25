from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel


class SeekerPrefCreate(BaseModel):
    service_id: uuid.UUID
    job_type: str
    work_mode: Optional[str] = None
    location: Dict[str, Any]
    work_schedule: Dict[str, Any]
    gender: Optional[str] = "any"
    age_range: Optional[Dict[str, Any]] = None