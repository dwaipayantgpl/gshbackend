from fastapi import APIRouter, Body, Depends

# Fixed imports: Point to the 'complaint' folder logic and dtos
from complaint.logic.service import get_all_complaints, submit_complaint, update_complaint_status
from complaint.structs.dtos import ComplaintCreate
from auth.logic.deps import get_current_account_id, require_admin

router = APIRouter()

@router.post("/user/complaints", summary="User: Submit a complaint")
async def user_submit(
    payload: ComplaintCreate, 
    account_id: str = Depends(get_current_account_id)
):
    return await submit_complaint(account_id, payload)

@router.get("/admin/usercomplaintsdata", summary="Admin: View all complaints")
async def admin_view_all(_admin: str = Depends(require_admin)):
    return await get_all_complaints()

@router.patch("/admin/complaints/{complaint_id}", summary="Admin: Resolve complaint")
async def admin_resolve(
    complaint_id: str, 
    status: str = Body(..., embed=True),
    _admin: str = Depends(require_admin)
):
    return await update_complaint_status(complaint_id, status)