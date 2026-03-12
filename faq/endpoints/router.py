

from fastapi import APIRouter, Depends, HTTPException
from auth.logic.deps import get_current_registration
from pydantic import BaseModel

from bookings.logic import service

router = APIRouter()

class FAQCreate(BaseModel):
    question: str
    answer: str

# 1. GET ALL (Public: Seeker, Helper, Admin)
@router.get("/", summary="View all FAQs")
async def get_faqs():
    return await service.get_all_faqs_logic()

# 2. POST (Admin Only)
@router.post("/create", summary="Admin creates an FAQ")
async def add_faq(data: FAQCreate, current_user = Depends(get_current_registration)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can create FAQs")
    return await service.create_faq_logic(data.question, data.answer)

# 3. DELETE (Admin Only)
@router.delete("/{faq_id}", summary="Admin deletes an FAQ")
async def remove_faq(faq_id: str, current_user = Depends(get_current_registration)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can delete FAQs")
    return await service.delete_faq_logic(faq_id)