from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ReviewCreateSchema(BaseModel):
    booking_id: UUID = Field(..., description="The ID of the specific booking being rated")
    helper_id: UUID = Field(..., description="The Registration ID of the helper being rated")
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: Optional[str] = Field(None, max_length=500)

    @validator('rating')
    def rating_must_be_valid(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5 stars')
        return v