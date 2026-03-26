import json

from db.tables import Notifiactions, Registration
from notifications.logic.socket import notif_manager


class NotificationService:
    @staticmethod
    async def trigger(
        user_id: str,
        title: str,
        content: str,
        category: str,
        booking_id=None,
        extra_metadata: dict = None,
    ):
        meta = extra_metadata or {}
        if booking_id:
            meta["booking_id"] = str(booking_id)

        new_notif = Notifiactions(
            recipient=user_id,
            category=category,
            title=title,
            content=content,
            booking_id=booking_id,
            metadata=meta,
        )
        await new_notif.save().run()

        payload = {
            "type": category,
            "title": title,
            "content": content,
            "metadata": meta,
        }

        was_sent_live = await notif_manager.send_to_user(str(user_id), payload)

        if was_sent_live:
            await (
                Notifiactions.update({Notifiactions.is_read: True})
                .where(Notifiactions.id == new_notif.id)
                .run()
            )

    @staticmethod
    async def get_unread_and_mark_read(user_id: str):
        unread = (
            await Notifiactions.objects()
            .where(
                (Notifiactions.recipient == user_id) & (Notifiactions.is_read == False)
            )
            .order_by(Notifiactions.created_at)
            .run()
        )

        if not unread:
            return []

        await (
            Notifiactions.update({Notifiactions.is_read: True})
            .where(Notifiactions.id.is_in([m.id for m in unread]))
            .run()
        )

        result = []
        for m in unread:
            meta_final = m.metadata
            if isinstance(m.metadata, str):
                try:
                    meta_final = json.loads(m.metadata)
                except:
                    meta_final = {}

            result.append(
                {
                    "notification_id": str(m.id),
                    "category": m.category,
                    "title": m.title,
                    "content": m.content,
                    "booking_id": str(m.booking_id) if m.booking_id else None,
                    "metadata": meta_final,
                    "created_at": m.created_at.isoformat(),
                }
            )
        return result

    @staticmethod
    async def get_unread_count(user_id: str):
        """Returns the count for the red badge on the app icon"""
        count = (
            await Notifiactions.count()
            .where(
                (Notifiactions.recipient == user_id) & (Notifiactions.is_read == False)
            )
            .run()
        )
        return count

    @staticmethod
    async def broadcast_new_service(
        service_name: str, description: str, service_id: str = None
    ):
        all_users = await Registration.objects().run()

        # Prepare metadata for both DB and WebSocket
        meta = {
            "service_id": str(service_id) if service_id else None,
            "service_name": service_name,
            "type": "new_service_announcement",
        }

        notif_objects = []
        for user in all_users:
            notif_objects.append(
                Notifiactions(
                    recipient=user.id,
                    category="admin_broadcast",
                    title="New Service Available! 🚀",
                    content=f"We just added '{service_name}': {description[:50]}...",
                    booking_id=service_id,  # Can store service_id here if column allows
                    metadata=meta,  # Storing the dict in JSONB column
                    is_read=False,
                )
            )

        # Bulk insert all notifications at once
        if notif_objects:
            await Notifiactions.insert(*notif_objects).run()

        # Push live to everyone currently online
        payload = {
            "type": "admin_broadcast",
            "title": "New Service Available! 🚀",
            "content": f"We just added '{service_name}' to our platform.",
            "metadata": meta,  # Include metadata here too
        }

        await notif_manager.broadcast(payload)
