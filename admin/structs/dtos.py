from datetime import datetime

from pydantic import BaseModel


class DeleteReason(BaseModel):
    reason: str


class StatusUpdate(BaseModel):
    reason: str


class BlockRequest(BaseModel):
    reason: str


class ComplaintCreate(BaseModel):
    subject: str
    description: str


class ComplaintOut(BaseModel):
    id: str
    account_id: str
    phone: str  # Useful for admin to see who to call
    subject: str
    description: str
    status: str
    created_at: datetime
