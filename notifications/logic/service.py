import json
import uuid
from typing import Any, Dict

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
            .offset(Notifiactions.created_at)
            .as_of(Notifiactions.created_at)
            .callback()
            .run()
        )

        if not unread:
            return []

        await (
            Notifiactions.update({Notifiactions.is_read: False})
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


async def get_my_notifications_logic(
    user_id: uuid.UUID, unread_only: bool = False, limit: int = 20, offset: int = 0
) -> Dict[str, Any]:
    """
    Business logic to fetch and count notifications for a specific user.
    """
    # 1. Base query filtered by recipient
    query = Notifiactions.select().where(Notifiactions.recipient == user_id)

    # 2. Filter by status if requested
    if unread_only:
        query = query.where(Notifiactions.is_read == False)

    # 3. Execute with sorting and pagination
    notifications = (
        await query.order_by(Notifiactions.created_at, ascending=False)
        .limit(limit)
        .offset(offset)
        .run()
    )

    # 4. Count total unread for the UI badge
    unread_count = (
        await Notifiactions.count()
        .where((Notifiactions.recipient == user_id) & (Notifiactions.is_read == False))
        .run()
    )

    return {
        "unread_count": unread_count,
        "count": len(notifications),
        "notifications": notifications,
    }


async def mark_as_read_logic(notification_id: uuid.UUID, user_id: uuid.UUID):
    """
    Business logic to mark a notification as read after verifying ownership.
    """
    notification = (
        await Notifiactions.objects()
        .where(
            (Notifiactions.id == notification_id) & (Notifiactions.recipient == user_id)
        )
        .first()
        .run()
    )

    if not notification:
        return False

    await (
        Notifiactions.update({Notifiactions.is_read: True})
        .where(Notifiactions.id == notification_id)
        .run()
    )

    return True


async def get_missed_notifications(registration_id: str):
    # Fetch notifications where is_read is False
    unread_notifications = (
        await Notifiactions.objects()
        .where(
            (Notifiactions.recipient == registration_id)
            & (Notifiactions.is_read == False)
        )
        .order_by(Notifiactions.created_at, ascending=False)
        .run()
    )

    # Format the data to match your developer's JSON requirement
    formatted_data = []
    for n in unread_notifications:
        formatted_data.append(
            {
                "notification_id": str(n.id),
                "category": n.category,
                "title": n.title,
                "content": n.content,
                "booking_id": str(n.booking_id) if n.booking_id else None,
                "metadata": n.metadata,  # This is already a JSONB field
                "created_at": n.created_at.isoformat(),
            }
        )
    formatted_data.append({
        "notification":str(n.id),
        "category":n.category                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
    })
    return {
        "type": "missed_notifications",
        "count": len(formatted_data),
        "data": formatted_data,
    }

