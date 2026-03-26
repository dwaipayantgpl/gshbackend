# C:\CompanyProject\gshbe\complaint\endpoints\router.py
from typing import List

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from auth.logic.deps import get_current_account_id, require_admin
from complaint.logic import service
from complaint.logic.service import (
    get_all_complaints,
    save_complaint_proof_logic,
    update_complaint_status,
)
from complaint.structs.dtos import ComplaintOut
from db.tables import Complaint, Registration

router = APIRouter()


@router.post("/submit", summary="User: Submit a complaint with file")
async def user_submit_complaint(
    category: str = Form(...),
    description: str = Form(...),
    booking_id: str = Form(None),
    file: UploadFile = File(None),
    account_id: str = Depends(get_current_account_id),
):
    proof_path = None

    # 1. Handle File Upload (JPG, PNG, PDF)
    if file:
        upload_result = await save_complaint_proof_logic(account_id, file)
        if upload_result["status"] == "error":
            raise HTTPException(status_code=400, detail=upload_result["message"])
        proof_path = upload_result["relative_path"]

    # 2. Save Complaint to Database
    new_complaint = Complaint(
        account_id=account_id,
        booking_id=booking_id,
        category=category,
        description=description,
        proof_image=proof_path,
        status="pending",
    )
    await new_complaint.save()

    return {
        "status": "success",
        "message": "Complaint submitted successfully.",
        "complaint_id": str(new_complaint.id),
    }


@router.get(
    "/admin/usercomplaintsdata",
    response_model=List[ComplaintOut],
    summary="Admin: View all complaints",
)
async def admin_view_all(_admin: str = Depends(require_admin)):
    return await get_all_complaints()


@router.patch("/admin/complaints/{complaint_id}", summary="Admin: Resolve complaint")
async def admin_resolve(
    complaint_id: str,
    status: str = Body(..., embed=True),
    _admin: str = Depends(require_admin),
):
    if status not in ["pending", "in_review", "resolved"]:
        raise HTTPException(status_code=400, detail="Invalid status transition")

    return await update_complaint_status(complaint_id, status)


# C:\CompanyProject\gshbe\complaint\endpoints\router.py


@router.get(
    "/history/{target_registration_id}",
    response_model=List[ComplaintOut],
    summary="Admin or Owner: View history",
)
async def get_complaint_history(
    target_registration_id: str,
    current_account_id: str = Depends(get_current_account_id),
):
    """
    Access rules:
    1. If the user is an Admin, allow access to any registration_id.
    2. If NOT Admin, verify the registration_id belongs to the logged-in account_id.
    """
    from uuid import UUID

    # 1. Fetch the target registration to find its owner (account)
    target_reg = (
        await Registration.objects()
        .where(Registration.id == UUID(target_registration_id))
        .first()
        .run()
    )

    if not target_reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    # 2. Check if the logged-in user is an admin
    is_admin = False
    current_reg = (
        await Registration.objects()
        .where(Registration.account == UUID(current_account_id))
        .first()
        .run()
    )

    if current_reg and current_reg.role == "admin":
        is_admin = True

    # 3. Ownership Check:
    # Compare the Account ID of the target registration with the current logged-in Account ID
    if not is_admin and str(target_reg.account) != str(current_account_id):
        raise HTTPException(
            status_code=403, detail="You do not have permission to view this history."
        )

    # 4. Call the logic using the Registration ID as requested by frontend
    result = await service.get_user_complaint_history_logic(target_registration_id)

    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.delete("/{complaint_id}", tags=["Admin Complaints"])
async def remove_complaint(
    complaint_id: str,
    _admin: str = Depends(require_admin),  # Only allows access if token is admin
):
    result = await service.delete_resolved_complaint(complaint_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result
