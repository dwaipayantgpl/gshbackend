from fastapi import APIRouter, Body, Depends

from auth.logic.deps import get_current_registration
from bookings.logic import service
router = APIRouter()
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from chat.logic.chat_manager import manager
from db.tables import ChatMessage, Registration
@router.websocket("/ws/chat/{booking_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, booking_id: str, user_id: str):
    # Retrieve user for role check (you might pass token instead for better security)
    user = await Registration.objects().get(Registration.id == user_id).run()
    
    try:
        # Validate permission before connecting
        await service.validate_chat_permission(booking_id, user_id, user.role)
        
        await manager.connect(websocket, booking_id)
        
        while True:
            data = await websocket.receive_text()
            
            # Save to DB
            new_msg = ChatMessage(
                booking=booking_id,
                sender=user_id,
                message=data
            )
            await new_msg.save()

            # Broadcast
            await manager.broadcast_to_room(booking_id, {
                "sender_id": user_id,
                "message": data,
                "timestamp": str(new_msg.created_at)
            })
            
    except Exception as e:
        print(f"Connection Error: {e}")
        manager.disconnect(websocket, booking_id)



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