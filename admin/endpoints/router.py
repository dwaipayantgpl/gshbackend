from fastapi import APIRouter, Body, Depends

from admin.endpoints import router
from admin.logic import admin_service
from admin.structs.dtos import ComplaintCreate
from auth.logic.deps import get_current_account_id, require_admin

router = APIRouter()


# last 1 month report
@router.get(
    "/analytics/last-month-report", summary="Admin: New users in the last 30 days"
)
async def last_month_report(_admin: str = Depends(require_admin)):
    return await admin_service.get_last_month_user_report()


# check details about services how many helper and seeker is join in each services
@router.get("/analytics/service-inventory", summary="Admin: Deep Service Analytics")
async def service_inventory_report(_admin: str = Depends(require_admin)):
    return await admin_service.get_service_deep_analytics()


# delete a user who have reputation
@router.delete("/users/{account_id}", summary="Admin: Permanent Delete & Blacklist")
async def delete_user_api(account_id: str, _admin: str = Depends(require_admin)):
    # Just pass the account_id
    return await admin_service.admin_delete_user_permanently(account_id)


# block-unblock
@router.get("/users/{account_id}/block")
async def block_user(account_id: str, _admin: str = Depends(require_admin)):
    return await admin_service.block_user_logic(account_id)


@router.delete("/users/{account_id}/unblock")
async def unblock_user(account_id: str, _admin: str = Depends(require_admin)):
    return await admin_service.unblock_user_logic(account_id)


@router.get("/blocked-users", summary="Admin: View all blocked users")
async def view_blocked(_admin: str = Depends(require_admin)):
    return await admin_service.get_all_blocked_users()


# get helper data api
@router.get("/helpers/counts", summary="Admin: Total/Active/Inactive Helper Stats")
async def get_helper_counts(_admin: str = Depends(require_admin)):
    return await admin_service.get_helper_status_stats()


# complain data api
@router.post("/user/complaints", summary="User: Submit a complaint")
async def user_submit(
    payload: ComplaintCreate, account_id: str = Depends(get_current_account_id)
):
    return await admin_service.submit_complaint(account_id, payload)


@router.get("/usercomplaintsdata", summary="Admin: View all complaints")
async def admin_view_all(_admin: str = Depends(require_admin)):
    return await admin_service.get_all_complaints()


@router.patch("/complaints/{complaint_id}", summary="Admin: Resolve complaint")
async def admin_resolve(
    complaint_id: str,
    status: str = Body(..., embed=True),
    _admin: str = Depends(require_admin),
):
    return await admin_service.update_complaint_status(complaint_id, status)
