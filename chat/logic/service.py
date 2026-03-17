# from fastapi import HTTPException
# from db.tables import ChatMessage, ServiceBooking

# async def validate_chat_permission(booking_id: str, sender_id: str, sender_role: str):
#     booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()
#     if not booking:
#         raise HTTPException(status_code=404, detail="Booking not found.")

#     if booking.status == 'cancelled':
#         raise HTTPException(
#             status_code=403, 
#             detail="Booking is cancelled. Chat is disabled."
#         )

#     is_seeker = str(booking.seeker) == sender_id
#     is_helper = str(booking.helper) == sender_id

#     if not (is_seeker or is_helper):
#         raise HTTPException(status_code=403, detail="Unauthorized.")

#     if sender_role == 'helper':
#         if booking.status == 'accepted':
#             return True

#         if booking.status == 'pending':
#             first_seeker_msg = await ChatMessage.objects().where(
#                 (ChatMessage.booking == booking_id) & 
#                 (ChatMessage.sender == booking.seeker)
#             ).first().run()

#             if not first_seeker_msg:
#                 raise HTTPException(
#                     status_code=403, 
#                     detail="Helper cannot send the first message for a pending request."
#                 )

#     return True


# async def get_chat_history_logic(booking_id: str, user_id: str, limit: int = 50):
#     # Ensure user belongs to the chat
#     booking = await ServiceBooking.objects().get(
#         (ServiceBooking.id == booking_id) & 
#         ((ServiceBooking.seeker == user_id) | (ServiceBooking.helper == user_id))
#     ).run()

#     if not booking:
#         from fastapi import HTTPException
#         raise HTTPException(status_code=403, detail="Unauthorized")

#     messages = await ChatMessage.objects().where(
#         ChatMessage.booking == booking_id
#     ).order_by(
#         ChatMessage.created_at, ascending=False # Piccolo syntax
#     ).limit(limit).run()

#     # Return in chronological order for UI
#     return messages[::-1]


import os
import shutil
import uuid

from fastapi import HTTPException, UploadFile
from db.tables import ChatMessage, ServiceBooking
from datetime import datetime


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
    if booking.status == 'cancelled':
        raise HTTPException(status_code=403, detail="Booking cancelled. Chat disabled.")

    is_seeker = str(booking.seeker) == sender_id
    is_helper = str(booking.helper) == sender_id
    if not (is_seeker or is_helper):
        raise HTTPException(status_code=403, detail="Unauthorized participant.")

    # Scenario 1 & 2: Helper logic
    if sender_role == 'helper':
        if booking.status == 'accepted':
            return True # Scenario 2
        
        if booking.status == 'pending':
            # Scenario 1: Only if seeker messaged first
            first_msg = await ChatMessage.objects().where(
                (ChatMessage.booking == booking_id) & (ChatMessage.sender == booking.seeker)
            ).first().run()
            if not first_msg:
                raise HTTPException(status_code=403, detail="Helper cannot start chat.")
    return True

async def get_unread_and_mark_read(booking_id: str, user_id: str):
    """Store-and-Forward: Fetch messages saved while user was offline"""
    unread = await ChatMessage.objects().where(
        (ChatMessage.booking == booking_id) & 
        (ChatMessage.receiver == user_id) & 
        (ChatMessage.is_read == False)
    ).order_by(ChatMessage.created_at).run()

    if unread:
        # Mark as read so they aren't delivered again
        await ChatMessage.update({ChatMessage.is_read: True}).where(
            ChatMessage.id.is_in([m.id for m in unread])
        ).run()
    
    return [
        {"id": str(m.id), "sender": str(m.sender), "message": m.message, "time": m.created_at.isoformat()} 
        for m in unread
    ]



async def get_chat_history_logic(booking_id: str, user_id: str):
    # Fetch messages for this booking
    # We order by created_at so the conversation flows correctly
    messages = await ChatMessage.objects().where(
        ChatMessage.booking == booking_id
    ).order_by(
        ChatMessage.created_at, ascending=True
    ).run()

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
            "timestamp": m.created_at.isoformat()
        }
        for m in messages
    ]