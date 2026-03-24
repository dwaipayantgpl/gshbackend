
import asyncio
import datetime

from fastapi import WebSocket
from typing import Dict, List

from db.tables import Account

class ChatManager:
    def __init__(self):
        # Structure: { "booking_id": { "registration_id": [ws1, ws2] } }
        self.rooms: Dict[str, Dict[str, List[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, booking_id: str, registration_id: str):
        if booking_id not in self.rooms:
            self.rooms[booking_id] = {}
        
        if registration_id not in self.rooms[booking_id]:
            self.rooms[booking_id][registration_id] = []
            
        self.rooms[booking_id][registration_id].append(websocket)

    def disconnect(self, websocket: WebSocket, booking_id: str, registration_id: str):
        if booking_id in self.rooms and registration_id in self.rooms[booking_id]:
            self.rooms[booking_id][registration_id].remove(websocket)
            
            # Senior's Rule: If no more sockets for this user, remove user_id
            if not self.rooms[booking_id][registration_id]:
                del self.rooms[booking_id][registration_id]
            
            # If no more users in the booking, remove booking_id
            if not self.rooms[booking_id]:
                del self.rooms[booking_id]

    async def broadcast_to_booking(self, booking_id: str, message: dict, exclude_registration_id: str = None):
        """
        Sends to everyone in the booking. 
        If exclude_registration_id is provided, it skips the sender's devices.
        """
        if booking_id in self.rooms:
            for user_id in self.rooms[booking_id]:
                
                if user_id == exclude_registration_id:
                    continue 
                for connection in self.rooms[booking_id][user_id]:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        continue

manager = ChatManager()


class PresenceManager:
    def __init__(self):
        self.users: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        
        if user_id not in self.users:
            self.users[user_id] = {"sockets": [], "grace_task": None}
            # Update DB immediately to Online
            await Account.update({
                Account.is_user_online: "online",
                Account.last_seen: datetime.now()
            }).where(Account.id == user_id).run()
        
        if self.users[user_id]["grace_task"]:
            self.users[user_id]["grace_task"].cancel()
            self.users[user_id]["grace_task"] = None

        self.users[user_id]["sockets"].append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.users:
            if websocket in self.users[user_id]["sockets"]:
                self.users[user_id]["sockets"].remove(websocket)
            
            # Start 60s timer ONLY if no tabs are left open
            if not self.users[user_id]["sockets"]:
                loop = asyncio.get_event_loop()
                self.users[user_id]["grace_task"] = loop.create_task(
                    self._mark_offline_after_delay(user_id)
                )

    async def _mark_offline_after_delay(self, user_id: str):
        try:
            await asyncio.sleep(60) # The 1-minute Grace Period
            
            # After 60s, update DB to Offline
            await Account.update({
                Account.is_user_online: "offline",
                Account.last_seen: datetime.now()
            }).where(Account.id == user_id).run()
            
            if user_id in self.users:
                del self.users[user_id]
                
        except asyncio.CancelledError:
            pass # User came back before 60s was up!

presence_manager = PresenceManager()