from datetime import date
from pydantic import BaseModel
from typing import List, Optional
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

class UserReportOut(BaseModel):
    account_id: str
    name: str
    phone: str
    role: str  # 'helper' or 'seeker'


class UserReportOut(BaseModel):
    account_id: str
    phone: str
    role: str  # 'helper' or 'seeker'



class UserReportDetail(BaseModel):
    account_id: str
    registration_id:str
    phone: str
    profile_picture: Optional[str] = None
    role: str
    capacity: str
    is_active: bool
    name: str
    city: str
    area: str

class AdminDashboardOut(BaseModel):
    total_helpers: int
    total_seekers: int
    users: List[UserReportDetail]

class DateRangeIn(BaseModel):
    start_date: date
    end_date: date