from fastapi import APIRouter, Depends, HTTPException

from auth.logic.deps import get_current_registration
from bookings.structs.dtos import ApplyToHelperSchema
from db.tables import Registration
from bookings.logic import service


router = APIRouter()

@router.post("/apply")
async def apply_to_helper(
    data: ApplyToHelperSchema, 
    current_reg: Registration = Depends(get_current_registration)
):
    return await service.apply_for_service_logic(str(current_reg.id), data)


@router.get("/received")
async def view_applications(
    current_reg: Registration = Depends(get_current_registration)
):
    applications = await service.get_received_applications(str(current_reg.id))
    
    if not applications:
        return {"message": "No pending applications found.", "data": []}
        
    return {"status": "success", "data": applications}


@router.patch("/respond/{booking_id}")
async def respond_to_booking(
    booking_id: str, 
    status: str, # 'accepted' or 'rejected'
    current_reg = Depends(get_current_registration)
):
    if status not in ["accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status.")

    return await service.respond_to_application_logic(
        booking_id, 
        str(current_reg.id), 
        status
    )