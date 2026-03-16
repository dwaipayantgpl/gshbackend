from fastapi import HTTPException
from db.tables import ChatMessage, ServiceBooking

async def validate_chat_permission(booking_id: str, sender_id: str, sender_role: str):
    # 1. Fetch the booking to verify relationship
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    is_seeker = str(booking.seeker) == sender_id
    is_helper = str(booking.helper) == sender_id

    # 2. Basic ownership check
    if not (is_seeker or is_helper):
        raise HTTPException(status_code=403, detail="You are not part of this booking.")

    # 3. Apply the "First Message" Rules
    if sender_role == 'helper':
        # Rule A: Helper can message if they have a booking request (Status check)
        # Assuming status 'pending' means seeker sent a request, or 'accepted' means active
        if booking.status in ['pending', 'accepted', 'confirmed']:
            return True

        # Rule B: Helper can message if the seeker has already sent at least one message
        first_seeker_msg = await ChatMessage.objects().where(
            (ChatMessage.booking == booking_id) & 
            (ChatMessage.sender == booking.seeker)
        ).first().run()

        if not first_seeker_msg:
            raise HTTPException(
                status_code=403, 
                detail="Helpers cannot initiate chat unless there is a booking request or the Seeker messages first."
            )

    # Seekers are allowed to message first by default as long as the booking entry exists
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