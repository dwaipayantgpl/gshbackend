from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from starlette import status

from auth.logic.deps import get_current_registration
from auth.logic.tokens import decode_access_token
from chat.logic import service
router = APIRouter()
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from chat.logic.chat_manager import manager
from db.tables import ChatMessage, Registration, ServiceBooking

# @router.websocket("/stream/{booking_id}/{account_id}")
# async def websocket_endpoint(websocket: WebSocket, booking_id: str, account_id: str):
#     # 1. ENFORCE AUTHORIZATION BEFORE ACCEPTING
#     auth_header = websocket.headers.get("authorization")
    
#     if not auth_header or not auth_header.startswith("Bearer "):
#         # Reject immediately if no token is present
#         await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#         return

#     token = auth_header.split(" ")[1]
    
#     try:
#         # 2. DECODE AND VERIFY
#         payload = decode_access_token(token)
#         token_sub = payload.get("sub") # This is usually the Account ID
        
#         # 3. IDENTITY MATCH
#         # Ensure the person connecting IS who they say they are in the URL
#         if str(token_sub) != str(account_id):
#             print(f"SECURITY ALERT: Token ID {token_sub} does not match URL ID {account_id}")
#             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#             return
            
#     except Exception as e:
#         print(f"AUTH ERROR: {e}")
#         await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#         return

#     # 4. IF AUTH PASSES, PROCEED
#     await websocket.accept() 
    
#     try:
#         # Lookup Registration profile (Same as your current logic)
#         user = await Registration.objects().where(
#             Registration.account == account_id
#         ).first().run()
        
#         if not user:
#             await websocket.send_json({"error": "Registration profile not found"})
#             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#             return

#         registration_id = str(user.id)

#         # Permission Check (Scenario 1, 2, and 3 logic)
#         try:
#             await service.validate_chat_permission(booking_id, registration_id, user.role)
#         except Exception as perm_err:
#             await websocket.send_json({"error": str(perm_err)})
#             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#             return

#         # Join Manager
#         await manager.connect(websocket, booking_id)
        
#         while True:
#             data = await websocket.receive_json()
#             message_text = data.get("message", "")
            
#             if message_text:
#                 new_msg = ChatMessage(
#                     booking=booking_id,
#                     sender=registration_id,
#                     message=message_text
#                 )
#                 await new_msg.save()

#                 await manager.broadcast_to_room(booking_id, {
#                     "sender_id": registration_id,
#                     "message": message_text,
#                     "timestamp": "Just now"
#                 })

#     except WebSocketDisconnect:
#         manager.disconnect(websocket, booking_id)
#     except Exception as e:
#         print(f"DEBUG: Unexpected Server Error: {e}")
#         if websocket.client_state.name != "DISCONNECTED":
#             await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# @router.get("/chat/history/{booking_id}")
# async def get_chat_history(
#     booking_id: str,
#     current_user: Registration = Depends(get_current_registration)
# ):
#     """
#     Returns the recent chat history between a Seeker and a Helper.
#     """
#     return await service.get_chat_history_logic(
#         booking_id, 
#         str(current_user.id)
#     )



@router.post("/send/{booking_id}")
async def send_unified_message(
    booking_id: str, 
    message: Optional[str] = Form(None), 
    file: Optional[UploadFile] = File(None), 
    sender: Registration = Depends(get_current_registration)
):
    # 1. Check permissions (Scenario 1, 2, 3)
    await service.validate_chat_permission(booking_id, str(sender.id), sender.role)

    # 2. Process File (if provided)
    file_url, file_name, file_type = await service.handle_file_upload(file)

    # 3. Identify Receiver
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()
    receiver_id = booking.helper if str(booking.seeker) == str(sender.id) else booking.seeker

    # 4. Save to Database (Ensuring no NULL values for NOT NULL columns)
    new_msg = ChatMessage(
        booking=booking_id,
        sender=sender.id,
        receiver=receiver_id,
        message=message if message is not None else "",
        file_url=file_url if file_url is not None else "",
        file_name=file_name if file_name is not None else "",
        file_type=file_type if file_type is not None else "",
        is_read=False
    )
    await new_msg.save()

    # 5. Broadcast to ALL active sockets
    # UPDATE: We now use new_msg.<property> to ensure the socket gets the same data as the DB
    await manager.broadcast_to_booking(booking_id, {
        "type": "new_message",
        "data": {
            "id": str(new_msg.id),
            "sender_id": str(sender.id),
            "receiver_id": str(receiver_id),
            "message": new_msg.message,   # Fixed: uses the string from DB
            "file_url": new_msg.file_url, # Fixed: uses the path from DB
            "file_name": new_msg.file_name,
            "file_type": new_msg.file_type,
            "timestamp": datetime.now().isoformat()
        }
    })

    return {"status": "success", "message":{
            "id": str(new_msg.id),
            "sender_id": str(sender.id),
            "receiver_id": str(receiver_id),
            "message": new_msg.message,   # Fixed: uses the string from DB
            "file_url": new_msg.file_url, # Fixed: uses the path from DB
            "file_name": new_msg.file_name,
            "file_type": new_msg.file_type,
            "timestamp": datetime.now().isoformat()
        }}

@router.websocket("/stream/{booking_id}/{account_id}")
async def websocket_endpoint(websocket: WebSocket, booking_id: str, account_id: str):
    # --- Auth Logic (Keep your existing token verification here) ---
    auth_header = websocket.headers.get("authorization")
    if not auth_header: return
    # ... (token decoding as per your snippet) ...
    
    await websocket.accept()
    
    try:
        user = await Registration.objects().where(Registration.account == account_id).first().run()
        reg_id = str(user.id)

        # 1. CATCH-UP: Send messages missed while offline
        unread_msgs = await service.get_unread_and_mark_read(booking_id, reg_id)
        if unread_msgs:
            await websocket.send_json({"type": "pending_messages", "data": unread_msgs})

        # 2. CONNECT: Register all device sockets
        await manager.connect(websocket, booking_id, reg_id)
        
        while True:
            await websocket.receive_text() # Keep-alive

    except WebSocketDisconnect:
        manager.disconnect(websocket, booking_id, reg_id)


# chat/endpoints/router.py

@router.get("/history/{booking_id}")
async def get_chat_history(
    booking_id: str,
    current_user: Registration = Depends(get_current_registration)
):
    # 1. Security check: Is this user part of this booking?
    # (Re-using your existing validation logic)
    await service.validate_chat_permission(
        booking_id, 
        str(current_user.id), 
        current_user.role
    )

    # 2. Fetch and return history
    history = await service.get_chat_history_logic(booking_id, str(current_user.id))
    
    return {
        "status": "success",
        "booking_id": booking_id,
        "history": history
    }

@router.patch("/messages/{message_id}")
async def edit_chat_message(
    message_id: str,
    message: str = Body(..., embed=True),
    current_user: Registration = Depends(get_current_registration)
):
    updated_message = await service.edit_chat_message_logic(
        message_id=message_id,
        user_id=str(current_user.id),
        user_role=current_user.role,
        new_message=message,
    )

    await manager.broadcast_to_booking(updated_message["booking_id"], {
        "type": "message_edited",
        "data": updated_message
    })

    return {
        "status": "success",
        "message": updated_message
    }


@router.delete("/messages/{message_id}")
async def delete_chat_message(
    message_id: str,
    current_user: Registration = Depends(get_current_registration)
):
    # grab snapshot before delete so we still know which booking to broadcast to
    existing_message = await ChatMessage.objects().where(
        ChatMessage.id == message_id
    ).first().run()

    delete_result = await service.delete_chat_message_logic(
        message_id=message_id,
        user_id=str(current_user.id),
        user_role=current_user.role,
    )

    if existing_message:
        await manager.broadcast_to_booking(str(existing_message.booking), {
            "type": "message_deleted",
            "data": {
                "id": message_id,
                "booking_id": str(existing_message.booking)
            }
        })

    return {
        "status": "success",
        **delete_result
    }

@router.get("/bookings")
async def get_my_chat_booking_ids(
    current_user: Registration = Depends(get_current_registration)
):
    chats = await service.get_user_chat_booking_ids_logic(str(current_user.id))

    return {
        "status": "success",
        "user_id": str(current_user.id),
        "chats": chats
    }