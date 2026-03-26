import os
import shutil
import uuid

from fastapi import HTTPException, UploadFile

from db.tables import ChatMessage, Registration, ServiceBooking

UPLOAD_DIR = r"C:\CompanyProject\gshbe\static\uploads\chat_upload"


async def handle_file_upload(file: UploadFile):
    if not file:
        return None, None, None

    # Ensure directory exists
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Create unique filename to prevent overwriting
    file_ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4()}{file_ext}"

    # full_path is for saving to disk
    full_path = os.path.join(UPLOAD_DIR, unique_name)

    # relative_url is for the database/frontend (assuming /static is mounted)
    relative_url = f"/static/uploads/chat_upload/{unique_name}"

    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return relative_url, file.filename, file.content_type


async def validate_chat_permission(booking_id: str, sender_id: str, sender_role: str):
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Scenario 3: Cancelled logic
    if booking.status == "cancelled":
        raise HTTPException(status_code=403, detail="Booking cancelled. Chat disabled.")

    is_seeker = str(booking.seeker) == sender_id
    is_helper = str(booking.helper) == sender_id
    if not (is_seeker or is_helper):
        raise HTTPException(status_code=403, detail="Unauthorized participant.")

    # Scenario 1 & 2: Helper logic
    if sender_role == "helper":
        if booking.status == "accepted":
            return True  # Scenario 2

        if booking.status == "pending":
            # Scenario 1: Only if seeker messaged first
            first_msg = (
                await ChatMessage.objects()
                .where(
                    (ChatMessage.booking == booking_id)
                    & (ChatMessage.sender == booking.seeker)
                )
                .first()
                .run()
            )
            if not first_msg:
                raise HTTPException(status_code=403, detail="Helper cannot start chat.")
    return True


async def get_unread_and_mark_read(booking_id: str, user_id: str):
    """Store-and-Forward: Fetch messages saved while user was offline"""
    unread = (
        await ChatMessage.objects()
        .where(
            (ChatMessage.booking == booking_id)
            & (ChatMessage.receiver == user_id)
            & (ChatMessage.is_read == False)
        )
        .order_by(ChatMessage.created_at)
        .run()
    )

    if unread:
        # Mark as read so they aren't delivered again
        await (
            ChatMessage.update({ChatMessage.is_read: True})
            .where(ChatMessage.id.is_in([m.id for m in unread]))
            .run()
        )

    return [
        {
            "id": str(m.id),
            "sender": str(m.sender),
            "message": m.message,
            "time": m.created_at.isoformat(),
        }
        for m in unread
    ]


async def get_chat_history_logic(booking_id: str, user_id: str):
    # Fetch messages for this booking
    # We order by created_at so the conversation flows correctly
    messages = (
        await ChatMessage.objects()
        .where(ChatMessage.booking == booking_id)
        .order_by(ChatMessage.created_at, ascending=True)
        .run()
    )

    return [
        {
            "id": str(m.id),
            "sender_id": str(m.sender),
            "receiver_id": str(m.receiver),
            "message": m.message,
            "file_url": m.file_url,
            "file_name": m.file_name,
            "file_type": m.file_type,
            "is_read": m.is_read,
            "timestamp": m.created_at.isoformat(),
        }
        for m in messages
    ]


async def edit_chat_message_logic(
    message_id: str, user_id: str, user_role: str, new_message: str
):
    message_obj = await ChatMessage.objects().get(ChatMessage.id == message_id).run()

    if not message_obj:
        raise HTTPException(status_code=404, detail="Message not found.")

    # only the sender can edit
    if str(message_obj.sender) != user_id:
        raise HTTPException(
            status_code=403, detail="You can only edit your own message."
        )

    # reuse existing booking-based permission logic
    await validate_chat_permission(str(message_obj.booking), user_id, user_role)

    cleaned_message = (new_message or "").strip()
    if not cleaned_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    await (
        ChatMessage.update({ChatMessage.message: cleaned_message})
        .where(ChatMessage.id == message_id)
        .run()
    )

    updated = await ChatMessage.objects().get(ChatMessage.id == message_id).run()

    return {
        "id": str(updated.id),
        "booking_id": str(updated.booking),
        "sender_id": str(updated.sender),
        "receiver_id": str(updated.receiver),
        "message": updated.message,
        "file_url": updated.file_url,
        "file_name": updated.file_name,
        "file_type": updated.file_type,
        "is_read": updated.is_read,
        "timestamp": updated.created_at.isoformat(),
    }


async def delete_chat_message_logic(message_id: str, user_id: str, user_role: str):
    message_obj = await ChatMessage.objects().get(ChatMessage.id == message_id).run()

    if not message_obj:
        raise HTTPException(status_code=404, detail="Message not found.")

    # only the sender can delete
    if str(message_obj.sender) != user_id:
        raise HTTPException(
            status_code=403, detail="You can only delete your own message."
        )

    # reuse existing booking-based permission logic
    await validate_chat_permission(str(message_obj.booking), user_id, user_role)

    # optional: remove uploaded file from disk too
    if message_obj.file_url:
        filename = os.path.basename(message_obj.file_url)
        full_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass

    await ChatMessage.delete().where(ChatMessage.id == message_id).run()

    return {"success": True, "message": "Chat message deleted successfully."}


async def get_user_chat_booking_ids_logic(user_id: str):
    messages = (
        await ChatMessage.objects()
        .where((ChatMessage.sender == user_id) | (ChatMessage.receiver == user_id))
        .order_by(ChatMessage.created_at, ascending=False)
        .run()
    )

    seen = set()
    temp_chats = []
    other_party_ids = set()

    for msg in messages:
        booking_id = str(msg.booking)
        if booking_id in seen:
            continue

        # Determine the other party's ID
        sender_id = str(msg.sender) if msg.sender else None
        receiver_id = str(msg.receiver) if msg.receiver else None

        other_party_reg_id = receiver_id if sender_id == user_id else sender_id

        # CRITICAL FIX: Only add to the list if it's not None and not the string "None"
        if other_party_reg_id and other_party_reg_id != "None":
            seen.add(booking_id)
            temp_chats.append(
                {
                    "booking_id": booking_id,
                    "other_party_registration_id": other_party_reg_id,
                }
            )
            other_party_ids.add(other_party_reg_id)

    # If no valid chats were found, return empty list early
    if not other_party_ids:
        return []

    # Bulk fetch using the corrected .is_in() method
    profiles = (
        await Registration.select(Registration.id, Registration.account)
        .where(Registration.id.is_in(list(other_party_ids)))
        .run()
    )

    profile_map = {str(p["id"]): str(p["account"]) for p in profiles}

    final_chats = []
    for chat in temp_chats:
        reg_id = chat["other_party_registration_id"]
        final_chats.append(
            {
                "booking_id": chat["booking_id"],
                "other_party_registration_id": reg_id,
                "other_party_account_id": profile_map.get(reg_id),
            }
        )

    return final_chats
