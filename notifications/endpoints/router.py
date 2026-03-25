import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from auth.logic.deps import get_current_registration
from db.tables import Registration
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
            await websocket.send_json({
                "type": "missed_notifications",
                "count": len(missed_data),
                "data": missed_data
            })

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
    return {
        "status": "success",
        "unread_count": count
    }