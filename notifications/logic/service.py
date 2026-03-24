from uuid import UUID
from db.tables import Notifiactions, Registration
# FIX: Import notif_manager from the socket file, not from service!
from notifications.logic.socket import notif_manager

class NotificationService:
    @staticmethod
    async def trigger(user_id: str, title: str, content: str, booking_id=None):
        # 1. Save to DB
        new_notif = Notifiactions(
            recipient=user_id,
            title=title,
            content=content,
            booking_id=booking_id
        )
        await new_notif.save().run()

        # 2. Push to WebSocket
        payload = {
            "title": title,
            "content": content,
            "booking_id": str(booking_id) if booking_id else None
        }
        await notif_manager.send_to_user(str(user_id), payload)
        
    @staticmethod
    async def notify_all(title: str, content: str, role: str = None):
        """Sends a notification to all users or a specific group."""
        query = Registration.select(Registration.id)
        if role:
            query = query.where(Registration.role == role)
        
        users = await query.run()
        for user in users:
            # FIX: Change 'notify' to 'trigger_notification' to match your method name
            await NotificationService.trigger_notification(
                user_id=str(user['id']),
                title=title,
                content=content
            )
        
    @staticmethod
    async def get_user_notifications(recipient_id: str):
        return await Notifiactions.select().where(
            Notifiactions.recipient == recipient_id
        ).order_by(
            Notifiactions.created_at, descending=True
        ).limit(20).run()
    
    @staticmethod
    async def get_unread_and_mark_read(user_id: str):
        unread = await Notifiactions.objects().where(
            (Notifiactions.recipient == user_id) & 
            (Notifiactions.is_read == False)
        ).order_by(Notifiactions.created_at).run()

        if unread:
            await Notifiactions.update({Notifiactions.is_read: True}).where(
                Notifiactions.id.is_in([m.id for m in unread])
            ).run()
            
        return [
            {
                "notification_id": str(m.id),
                "title": m.title,
                "content": m.content,
                "booking_id": str(m.booking_id) if m.booking_id else None,
                "created_at": m.created_at.isoformat()
            } for m in unread
        ]