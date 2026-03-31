from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends

import bookings
from admin.endpoints import router
from admin.logic import admin_service
from admin.structs.dtos import ComplaintCreate
from auth.logic.deps import get_current_account_id, require_admin
from db.tables import ServiceBooking

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

router.get("/booking-volume")
async def get_booking_volume(days: int = 7,_admin: str = Depends(require_admin)):
    start_date = datetime.date.today() - datetime.timedelta(days=days)
    
    # Raw SQL is best for Date Grouping in Postgres
    query = f"""
        SELECT TO_CHAR(created_at, 'YYYY-MM-DD') as date, COUNT(id) as total 
        FROM bookings 
        WHERE created_at >= '{start_date}'
        GROUP BY date ORDER BY date ASC
    """
    stats = await ServiceBooking.raw(query).run()
    return {"chart_type": "line", "dataset": stats}

router.get("/completion-rate")
async def get_completion_rate():
    data = await ServiceBooking.raw("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
        FROM ServiceBooking
    """).run()
    
    res = data[0]
    total = res['total']
    rate = (res['completed'] / total * 100) if total > 0 else 0
    
    return {
        "summary": res,
        "success_percentage": round(rate, 2),
        "health_status": "Healthy" if rate > 70 else "Needs Attention"
    }
router.get("/top-categories")
async def get_top_categories():
    # Identifies what seekers are searching for most
    results = await ServiceBooking.raw("""
        SELECT category, COUNT(id) as booking_count 
        FROM bookings 
        GROUP BY category 
        ORDER BY booking_count DESC 
        LIMIT 5
    """).run()
    return {"chart_type": "pie", "data": results}

router.get("/take-most")
async def gettoken():
    results=await ServiceBooking.raw("""
    select category,count(id) as booking_count
    from bookings
    group by ccategory
    order by booking_count desc
 """).run()
    return {"char_type":"pie","data":results}


