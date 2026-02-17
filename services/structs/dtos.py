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


class ServiceUpdateIn(BaseModel):
    name: Optional[str] = None         # Optional for patching
    description: Optional[str] = None  # Optional for patching

class ServiceStasOut(BaseModel):
    service:str
    helper:int
    seeker:int