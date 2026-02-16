from pydantic import BaseModel
from typing import Optional
import uuid

class ServiceCreateIn(BaseModel):
    name: str
    description: Optional[str] = None

class ServiceOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True