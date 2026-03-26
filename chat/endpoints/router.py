from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile
from starlette import status

from auth.logic.deps import get_current_registration
from auth.logic.tokens import decode_access_token
from chat.logic import service
from notifications.logic.service import NotificationService

router = APIRouter()
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from chat.logic.chat_manager import PresenceManager, manager
from db.tables import (
    ChatMessage,
    HelperInstitutional,
    HelperPersonal,
    Registration,
    SeekerInstitutional,
    SeekerPersonal,
    ServiceBooking,
)


@router.post("/send/{booking_id}")
async def send_unified_message(
    booking_id: str,
    message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    sender: Registration = Depends(get_current_registration),
):
    # 1. Check permissions (Scenario 1, 2, 3)
    await service.validate_chat_permission(booking_id, str(sender.id), sender.role)

    # 2. Process File (if provided)
    file_url, file_name, file_type = await service.handle_file_upload(file)

    # 3. Identify Receiver
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()
    receiver_id = (
        booking.helper if str(booking.seeker) == str(sender.id) else booking.seeker
    )

    # 4. Save to Database (Ensuring no NULL values for NOT NULL columns)
    new_msg = ChatMessage(
        booking=booking_id,
        sender=sender.id,
        receiver=receiver_id,
        message=message if message is not None else "",
        file_url=file_url if file_url is not None else "",
        file_name=file_name if file_name is not None else "",
        file_type=file_type if file_type is not None else "",
        is_read=False,
    )
    await new_msg.save()

    # 5. Broadcast to ALL active sockets
    # UPDATE: We now use new_msg.<property> to ensure the socket gets the same data as the DB
    await manager.broadcast_to_booking(
        booking_id,
        {
            "type": "new_message",
            "data": {
                "id": str(new_msg.id),
                "sender_id": str(sender.id),
                "receiver_id": str(receiver_id),
                "message": new_msg.message,  # Fixed: uses the string from DB
                "file_url": new_msg.file_url,  # Fixed: uses the path from DB
                "file_name": new_msg.file_name,
                "file_type": new_msg.file_type,
                "created_at": new_msg.created_at.isoformat(),
            },
        },
    )

    try:
        target_id = str(receiver_id).lower()
        sender_display_name = "User"

        # 1. Determine which profile table to check based on role and capacity
        role = sender.role  # from Registration table
        capacity = sender.capacity  # from Registration table

        profile = None
        if role == "seeker":
            if capacity == "personal":
                profile = (
                    await SeekerPersonal.objects()
                    .get(SeekerPersonal.registration == sender.id)
                    .run()
                )
            else:
                profile = (
                    await SeekerInstitutional.objects()
                    .get(SeekerInstitutional.registration == sender.id)
                    .run()
                )
        elif role == "helper":
            if capacity == "personal":
                profile = (
                    await HelperPersonal.objects()
                    .get(HelperPersonal.registration == sender.id)
                    .run()
                )
        else:
            profile = (
                await HelperInstitutional.objects()
                .get(HelperInstitutional.registration == sender.id)
                .run()
            )

        if profile and hasattr(profile, "name") and profile.name:
            sender_display_name = profile.name

        # 3. Trigger the notification
        await NotificationService.trigger(
            user_id=target_id,
            title=f"New Message from {sender_display_name}",
            content=f"{new_msg.message}",
            category="chat",
            booking_id=str(booking_id),
            extra_metadata={
                "sender_id": str(sender.id),
                "sender_name": sender_display_name,
                "chat_id": str(new_msg.id),
                "booking_id": str(booking_id),
            },
        )
        print(f"✅ Sent notification to {target_id} as '{sender_display_name}'")

    except Exception as e:
        print(f"❌ Notification name resolution failed: {e}")
        # Fallback if query fails
        await NotificationService.trigger(
            user_id=str(receiver_id).lower(),
            title="New Message",
            content=f"{new_msg.message}",
            category="chat",
            booking_id=str(booking_id),
            extra_metadata={"sender_name": "User"},
        )
    return {
        "status": "success",
        "message": {
            "id": str(new_msg.id),
            "sender_id": str(sender.id),
            "receiver_id": str(receiver_id),
            "message": new_msg.message,  # Fixed: uses the string from DB
            "file_url": new_msg.file_url,  # Fixed: uses the path from DB
            "file_name": new_msg.file_name,
            "file_type": new_msg.file_type,
            "created_at": new_msg.created_at.isoformat(),
        },
    }


@router.websocket("/stream/{booking_id}")
async def websocket_endpoint(
    websocket: WebSocket, booking_id: str, token: str = Query(None)
):
    # 1. AUTHENTICATION
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Clean the token if "Bearer " is present
        actual_token = token.replace("Bearer ", "")
        payload = decode_access_token(actual_token)

        # EXTRACT ACCOUNT ID FROM TOKEN
        account_id = payload.get("sub")

        if not account_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except Exception as e:
        print(f"Auth Error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. DATA RETRIEVAL & VALIDATION
    # Accept the connection first to send logic-based errors if needed
    await websocket.accept()

    try:
        # Find the registration profile using the ID from the TOKEN
        user = (
            await Registration.objects()
            .where(Registration.account == account_id)
            .first()
            .run()
        )

        if not user:
            await websocket.send_json({"error": "User profile not found"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        reg_id = str(user.id)

        # 3. PERMISSION CHECK
        # Ensure this user actually belongs to this booking
        try:
            await service.validate_chat_permission(booking_id, reg_id, user.role)
        except Exception as perm_err:
            await websocket.send_json({"error": str(perm_err)})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 4. ACTIVE CHAT LOGIC
        # Catch-up: Send messages missed while offline
        unread_msgs = await service.get_unread_and_mark_read(booking_id, reg_id)
        if unread_msgs:
            await websocket.send_json({"type": "pending_messages", "data": unread_msgs})

        # Connect to manager
        await manager.connect(websocket, booking_id, reg_id)

        while True:
            # Keep-alive loop
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket, booking_id, reg_id)
    except Exception as e:
        print(f"Unexpected Socket Error: {e}")


# chat/endpoints/router.py


@router.get("/history/{booking_id}")
async def get_chat_history(
    booking_id: str, current_user: Registration = Depends(get_current_registration)
):
    # 1. Security check: Is this user part of this booking?
    # (Re-using your existing validation logic)
    await service.validate_chat_permission(
        booking_id, str(current_user.id), current_user.role
    )

    # 2. Fetch and return history
    history = await service.get_chat_history_logic(booking_id, str(current_user.id))

    return {"status": "success", "booking_id": booking_id, "history": history}


@router.patch("/messages/{message_id}")
async def edit_chat_message(
    message_id: str,
    message: str = Body(..., embed=True),
    current_user: Registration = Depends(get_current_registration),
):
    updated_message = await service.edit_chat_message_logic(
        message_id=message_id,
        user_id=str(current_user.id),
        user_role=current_user.role,
        new_message=message,
    )

    await manager.broadcast_to_booking(
        updated_message["booking_id"],
        {"type": "message_edited", "data": updated_message},
    )

    return {"status": "success", "message": updated_message}


@router.delete("/messages/{message_id}")
async def delete_chat_message(
    message_id: str, current_user: Registration = Depends(get_current_registration)
):
    # grab snapshot before delete so we still know which booking to broadcast to
    existing_message = (
        await ChatMessage.objects().where(ChatMessage.id == message_id).first().run()
    )

    delete_result = await service.delete_chat_message_logic(
        message_id=message_id,
        user_id=str(current_user.id),
        user_role=current_user.role,
    )

    if existing_message:
        await manager.broadcast_to_booking(
            str(existing_message.booking),
            {
                "type": "message_deleted",
                "data": {"id": message_id, "booking_id": str(existing_message.booking)},
            },
        )

    return {"status": "success", **delete_result}


@router.get("/bookings")
async def get_my_chat_booking_ids(
    current_user: Registration = Depends(get_current_registration),
):
    chats = await service.get_user_chat_booking_ids_logic(str(current_user.id))

    return {"status": "success", "user_id": str(current_user.id), "chats": chats}


@router.websocket("/presence")
async def presence_socket(websocket: WebSocket, token: str = Query(None)):
    await websocket.accept()

    if not token:
        await websocket.send_json({"error": "No token"})
        await websocket.close()
        return

    try:
        payload = decode_access_token(token.replace("Bearer ", ""))
        user_id = payload.get("sub")

        await PresenceManager.connect(websocket, user_id)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        await PresenceManager.disconnect(websocket, user_id)
    except Exception:
        await websocket.close()
