from fastapi import APIRouter, Body, Depends

from auth.logic.deps import get_current_registration
from chat.logic import service
router = APIRouter()
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from chat.logic.chat_manager import manager
from db.tables import ChatMessage, Registration

@router.websocket("/stream/{booking_id}/{account_id}") # Note: URL now takes account_id
async def websocket_endpoint(websocket: WebSocket, booking_id: str, account_id: str):
    await websocket.accept()
    
    try:
        # 1. NEW STEP: Look up the Registration linked to this Account
        # We assume one Account has one Registration (or you pick the first one)
        user = await Registration.objects().where(
            Registration.account == account_id
        ).first().run()
        
        if not user:
            print(f"DEBUG: No Registration found for Account ID: {account_id}")
            await websocket.send_json({"error": "Registration profile not found for this account"})
            await websocket.close(code=1008)
            return

        # 2. Extract the TRUE Registration ID
        registration_id = str(user.id)
        print(f"DEBUG: Account {account_id} is using Registration {registration_id}")

        # 3. Permission Check using the Registration ID
        try:
            # We pass the registration_id here because bookings use Reg IDs
            await service.validate_chat_permission(booking_id, registration_id, user.role)
        except Exception as perm_err:
            print(f"DEBUG: Permission Denied: {perm_err}")
            await websocket.send_json({"error": str(perm_err)})
            await websocket.close(code=1008)
            return

        # 4. Join Manager
        await manager.connect(websocket, booking_id)
        
        while True:
            data = await websocket.receive_json()
            message_text = data.get("message", "")
            
            if message_text:
                new_msg = ChatMessage(
                    booking=booking_id,
                    sender=registration_id, # Save using Reg ID
                    message=message_text
                )
                await new_msg.save()

                await manager.broadcast_to_room(booking_id, {
                    "sender_id": registration_id,
                    "message": message_text,
                    "timestamp": "Just now"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, booking_id)
    except Exception as e:
        print(f"DEBUG: Unexpected Server Error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=1011)


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