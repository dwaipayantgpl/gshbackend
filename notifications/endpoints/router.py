from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from notifications.logic.service import NotificationService
from notifications.logic.socket import notif_manager

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def notification_endpoint(websocket: WebSocket, user_id: str):
    await notif_manager.connect(websocket, user_id)
    
    try:
        missed_data = await NotificationService.get_unread_and_mark_read(user_id)
        
        if missed_data:
            await websocket.send_json({
                "type": "missed_notifications",
                "count": len(missed_data),
                "data": missed_data
            })

        while True:
            await websocket.receive_text() # Heartbeat
            
    except WebSocketDisconnect:
        notif_manager.disconnect(websocket, user_id)