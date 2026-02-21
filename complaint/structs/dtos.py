from pydantic import BaseModel
from datetime import datetime

class ComplaintCreate(BaseModel):
    subject: str
    description: str

class ComplaintOut(BaseModel):
    id: str
    account_id: str
    phone: str # Useful for admin to see who to call
    subject: str
    description: str
    status: str
    created_at: datetime