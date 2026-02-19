from fastapi import APIRouter, Depends
import admin
from admin.endpoints import router
from admin.logic import admin_service
from admin.structs.dtos import BlockRequest, DeleteReason, StatusUpdate
from auth.logic.deps import require_admin
router = APIRouter()

#last 1 month report
@router.get("/analytics/last-month-report", summary="Admin: New users in the last 30 days")
async def last_month_report(
    _admin: str = Depends(require_admin)
):
    return await admin_service.get_last_month_user_report()


#check details about services how many helper and seeker is join in each services 
@router.get("/analytics/service-inventory", summary="Admin: Deep Service Analytics")
async def service_inventory_report(
    _admin: str = Depends(require_admin)
):
    return await admin_service.get_service_deep_analytics()

#delete a user who have reputation
@router.delete("/users/{account_id}", summary="Admin: Permanent Delete & Blacklist")
async def delete_user_api(
    account_id: str,
    payload: DeleteReason, # This is your Pydantic model
    _admin: str = Depends(require_admin)
):
    # Pass payload.reason instead of just reason
    return await admin_service.admin_delete_user_permanently(account_id, payload.reason)


#block-unblock
@router.post("/users/{account_id}/block")
async def block_user(account_id: str, payload: BlockRequest):
    return await admin_service.block_user_logic(account_id, payload.reason)

@router.delete("/users/{account_id}/unblock")
async def unblock_user(account_id: str):
    return await admin_service.unblock_user_logic(account_id)


#get helper data api
@router.get("/helpers/counts", summary="Admin: Total/Active/Inactive Helper Stats")
async def get_helper_counts(
    _admin: str = Depends(require_admin)
):
    return await admin_service.get_helper_status_stats()