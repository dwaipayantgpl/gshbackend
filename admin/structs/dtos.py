from datetime import date
from pydantic import BaseModel
from typing import List, Optional
import uuid
class DeleteReason(BaseModel):
    reason: str

class StatusUpdate(BaseModel):
    reason: str

class BlockRequest(BaseModel):
    reason: str