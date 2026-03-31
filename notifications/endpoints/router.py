import asyncio

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from starlette import status

from auth.logic.deps import get_current_registration
from db.tables import Registration
from notifications.logic import service
from notifications.logic.service import NotificationService
from notifications.logic.socket import notif_manager

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def notification_endpoint(websocket: WebSocket, user_id: str):
    # Register the connection
    await notif_manager.connect(websocket, user_id)

    try:
        # Give the event loop a tiny breath to finalize the TCP handshake
        await asyncio.sleep(0.1)

        # Fetch missed notifications
        missed_data = await NotificationService.get_unread_and_mark_read(user_id)

        if missed_data:
            # Send them as a single batch
            await websocket.send_json(
                {
                    "type": "missed_notifications",
                    "count": len(missed_data),
                    "data": missed_data,
                }
            )

        # Keep alive
        while True:
            data = await websocket.receive_text()
            # Optional: handle client-side pings here

    except WebSocketDisconnect:
        notif_manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WS Error: {e}")
        notif_manager.disconnect(websocket, user_id)


@router.get("/unread-count")
async def get_count(current_user: Registration = Depends(get_current_registration)):
    count = await NotificationService.get_unread_count(str(current_user.id))
    return {"status": "success", "unread_count": count}


@router.get("/my-notifications")
async def get_my_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Registration = Depends(get_current_registration),
):
    """
    Endpoint to fetch notifications for the logged-in user.
    Uses 'Authorization: Bearer <token>'
    """
    try:
        data = await service.get_my_notifications_logic(
            user_id=current_user.id, unread_only=unread_only, limit=limit, offset=offset
        )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}",
        )


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: str, current_user: Registration = Depends(get_current_registration)
):
    """
    Endpoint to mark a single notification as read.
    """
    import uuid

    try:
        notif_uuid = uuid.UUID(notification_id)
        success = await service.mark_as_read_logic(notif_uuid, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied.",
            )

        return {"status": "success", "message": "Marked as read"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@router.get("/missed")
async def fetch_missed_notifications(
    registration_id: str = Depends(get_current_registration),
):
    """
    Securely fetch notifications for the logged-in user only.
    """
    try:
        # Now we use the ID extracted from the Token
        result = await service.get_missed_notifications(registration_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
