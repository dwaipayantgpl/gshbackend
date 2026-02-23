import uuid

from pydantic import BaseModel


class SeekerPrefCreate(BaseModel):
    service_id: uuid.UUID
    city: str
    area: str
    job_type: str = "full_time"