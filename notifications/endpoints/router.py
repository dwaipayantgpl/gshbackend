from fastapi import APIRouter, Depends

from auth.logic.deps import get_current_registration
from db.tables import Registration
from notifications.logic import service


router = APIRouter()
@router.get("/")
async def list_my_notifications(current_reg:Registration=Depends(get_current_registration)):
    data = await service.NotificationService.get_user_notifications(str(current_reg.id))
    unread = await service.NotificationService.get_unread_count(str(current_reg.id))
    return {"status": "success", "unread_count": unread, "notifications": data}

@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, current_reg: Registration = Depends(get_current_registration)):
    """Call this when the user clicks a notification."""
    await service.NotificationService.mark_as_read(notification_id, str(current_reg.id))
    return {"status": "success"}