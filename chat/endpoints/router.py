from fastapi import APIRouter, Body, Depends

from auth.logic.deps import get_current_registration
from bookings.logic import service
router = APIRouter()
# bookings/endpoints/chat_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from chat.logic.chat_manager import manager
from db.tables import ChatMessage, Registration

@router.websocket("/ws/chat/{booking_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, booking_id: str, user_id: str):
    await manager.connect(websocket, booking_id)
    try:
        while True:
            # Receive message from Seeker or Helper
            data = await websocket.receive_text()
            
            # 1. Save to Database instantly
            new_msg = ChatMessage(
                booking=booking_id,
                sender=user_id,
                message=data
            )
            await new_msg.save()

            # 2. Broadcast to everyone in the "Match Room"
            payload = {
                "sender_id": user_id,
                "message": data,
                "timestamp": str(new_msg.created_at)
            }
            await manager.broadcast_to_room(booking_id, payload)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, booking_id)


# bookings/endpoints/chat_router.py

@router.get("/chat/history/{booking_id}")
async def get_chat_history(
    booking_id: str,
    current_user: Registration = Depends(get_current_registration)
):
    """
    Returns the recent chat history between a Seeker and a Helper.
    """
    return await service.get_chat_history_logic(
        booking_id, 
        str(current_user.id)
    )