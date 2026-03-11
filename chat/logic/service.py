from http.client import HTTPException

from db.tables import ChatMessage, ServiceBooking

async def get_chat_history_logic(booking_id: str, user_id: str, limit: int = 50):
    # 1. Security Check: Is this user part of this booking?
    booking = await ServiceBooking.objects().get(
        (ServiceBooking.id == booking_id) & 
        ((ServiceBooking.seeker == user_id) | (ServiceBooking.helper == user_id))
    ).run()

    if not booking:
        raise HTTPException(status_code=403, detail="You are not authorized to view this chat.")

    # 2. Fetch messages ordered by newest first
    messages = await ChatMessage.select(
        ChatMessage.all_columns()
    ).where(
        ChatMessage.booking == booking_id
    ).order_by(
        ChatMessage.created_at, 
        descending=True  # <--- This replaces the need for 'Desc'
    ).limit(limit).run()

    return messages[::-1]