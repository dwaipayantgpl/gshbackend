from fastapi import APIRouter, Body, Depends
from starlette import status

from auth.logic.deps import get_current_registration
from auth.logic.tokens import decode_access_token
from chat.logic import service
router = APIRouter()
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from chat.logic.chat_manager import manager
from db.tables import ChatMessage, Registration

@router.websocket("/stream/{booking_id}/{account_id}")
async def websocket_endpoint(websocket: WebSocket, booking_id: str, account_id: str):
    # 1. ENFORCE AUTHORIZATION BEFORE ACCEPTING
    auth_header = websocket.headers.get("authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        # Reject immediately if no token is present
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    token = auth_header.split(" ")[1]
    
    try:
        # 2. DECODE AND VERIFY
        payload = decode_access_token(token)
        token_sub = payload.get("sub") # This is usually the Account ID
        
        # 3. IDENTITY MATCH
        # Ensure the person connecting IS who they say they are in the URL
        if str(token_sub) != str(account_id):
            print(f"SECURITY ALERT: Token ID {token_sub} does not match URL ID {account_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except Exception as e:
        print(f"AUTH ERROR: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 4. IF AUTH PASSES, PROCEED
    await websocket.accept() 
    
    try:
        # Lookup Registration profile (Same as your current logic)
        user = await Registration.objects().where(
            Registration.account == account_id
        ).first().run()
        
        if not user:
            await websocket.send_json({"error": "Registration profile not found"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        registration_id = str(user.id)

        # Permission Check (Scenario 1, 2, and 3 logic)
        try:
            await service.validate_chat_permission(booking_id, registration_id, user.role)
        except Exception as perm_err:
            await websocket.send_json({"error": str(perm_err)})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Join Manager
        await manager.connect(websocket, booking_id)
        
        while True:
            data = await websocket.receive_json()
            message_text = data.get("message", "")
            
            if message_text:
                new_msg = ChatMessage(
                    booking=booking_id,
                    sender=registration_id,
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
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


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