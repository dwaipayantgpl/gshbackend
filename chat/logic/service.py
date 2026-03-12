from fastapi import HTTPException
from db.tables import ChatMessage, ServiceBooking

async def validate_chat_permission(booking_id: str, sender_id: str, sender_role: str):
    # 1. Fetch the booking
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # 2. Check if user is part of this booking
    is_seeker = str(booking.seeker) == sender_id
    is_helper = str(booking.helper) == sender_id

    if not (is_seeker or is_helper):
        raise HTTPException(status_code=403, detail="You are not part of this booking.")

    # 3. HELPER SPECIAL RULE: Can only send first if a booking exists
    if sender_role == 'helper':
        # If the booking exists (which we verified above), the helper is allowed 
        # to message even if the seeker hasn't messaged yet.
        return True

    return True


async def get_chat_history_logic(booking_id: str, user_id: str, limit: int = 50):
    # Ensure user belongs to the chat
    booking = await ServiceBooking.objects().get(
        (ServiceBooking.id == booking_id) & 
        ((ServiceBooking.seeker == user_id) | (ServiceBooking.helper == user_id))
    ).run()

    if not booking:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Unauthorized")

    messages = await ChatMessage.objects().where(
        ChatMessage.booking == booking_id
    ).order_by(
        ChatMessage.created_at, ascending=False # Piccolo syntax
    ).limit(limit).run()

    # Return in chronological order for UI
    return messages[::-1]