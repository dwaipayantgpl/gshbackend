from uuid import UUID
from db.tables import Notifiactions
import notifications
from .socket import sio, online_users

class NotificationService:
    @staticmethod
    async def notify(recipient_id: str, title: str, content: str, booking_id: UUID = None):
        # 1. Save to Database (The History)
        new_notif = notifications(
            recipient=recipient_id,
            title=title,
            content=content,
            booking_id=booking_id
        )
        await new_notif.save().run()

        # 2. Check if user is LIVE (Socket.IO)
        sid = online_users.get(str(recipient_id))
        if sid:
            await sid.emit("notification", {
                "id": str(new_notif.id),
                "title": title,
                "content": content,
                "booking_id": str(booking_id) if booking_id else None,
                "created_at": str(new_notif.created_at)
            }, to=sid)
            return "live_sent"
        
        return "saved_to_db"
        
    @staticmethod
    async def get_user_notifications(recipient_id:str):
        return await Notifiactions.select().where(
        Notifiactions.recipient==recipient_id
        ).order_by(
            Notifiactions.created_at,descending=True
        ).limit(20).run()
    
    @staticmethod
    async def get_unread_count(recipient_id: str):
        """Returns the number of unread alerts for the 'Red Dot' in the UI."""
        return await notifications.count().where(
            (notifications.recipient == recipient_id) &
            (notifications.is_read == False)
        ).run()
    
    @staticmethod
    async def mark_as_read(notification_id: UUID, recipient_id: str):
        """Marks a specific notification as read."""
        await notifications.update({
            notifications.is_read: True
        }).where(
            (notifications.id == notification_id) &
            (notifications.recipient == recipient_id)
        ).run()