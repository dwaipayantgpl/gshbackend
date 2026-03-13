

from fastapi import APIRouter, Depends, HTTPException
from auth.logic.deps import get_current_registration
from pydantic import BaseModel

from faq.logic import service
from faq.structs.dtos import FAQCreate

router = APIRouter()

@router.get("/my-faqs")
async def get_user_faqs(current_user = Depends(get_current_registration)):
    return await service.get_faqs_by_role(current_user.role)

# 2. GET ALL (Admin view to see all management)
@router.get("/admin/all")
async def get_all_faqs_admin(current_user = Depends(get_current_registration)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
    return await service.admin_get_all_faqs()

# 3. POST (Admin Only)
@router.post("/create")
async def add_faq(data: FAQCreate, current_user = Depends(get_current_registration)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    return await service.create_faq_logic(data.question, data.answer, data.target_role)

# 3. DELETE (Admin Only)
@router.delete("/{faq_id}", summary="Admin deletes an FAQ")
async def remove_faq(faq_id: str, current_user = Depends(get_current_registration)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can delete FAQs")
    return await service.delete_faq_logic(faq_id)